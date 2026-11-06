"""Configured OAuth trust, strict claims and fresh delegated authorization.

No provider diagnostics or credential values form part of the public errors.
Only public verification keys and bounded exchanged access tokens are cached.
"""

from __future__ import annotations

import base64
import contextvars
import hashlib
import json
import os
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import jwt
import requests

READ = "onto.mcp.read"
WRITE = "onto.mcp.write"
ACCESS_TOKEN = "urn:ietf:params:oauth:token-type:access_token"
MARKERS = {
    "act",
    "onto_impersonator_id",
    "onto_impersonator_username",
    "onto_impersonator_client",
}
READ_TOOLS = frozenset(
    [
        "how_to_use_onto_mcp",
        "about_onto",
        "about_realm",
        "getOntoAIThreadID",
        "list_available_realms",
        "list_realm_agents",
        "get_realm_agent",
        "preflight_realm_agent_governance_proposal",
        "get_clone_object_to_realm_result",
        "search_templates",
        "search_relation_templates",
        "search_entities_by_relations",
        "search_agent_memory",
        "get_agent_memory_record",
        "get_memory_artifact",
        "get_memory_artifact_by_path",
        "get_own_memory_artifact_draft_by_path",
        "search_memory_artifacts",
        "search_objects",
        "get_template",
        "get_entity",
        "get_node_chat_messages",
        "search_entities",
        "search_entities_by_fields",
        "search_entities_with_related_meta",
        "search_diagrams",
        "search_context_tags",
        "get_diagram",
    ]
)
# Classification is explicit; adding a registration does not silently grant write authority.
WRITE_TOOLS = frozenset(
    [
        "saveOntoAIThreadID",
        "admit_realm_agent",
        "clone_object_to_realm",
        "create_memory_artifact_draft",
        "update_memory_artifact_draft",
        "append_memory_artifact",
        "submit_memory_artifact",
        "accept_memory_artifact",
        "revoke_memory_artifact",
        "supersede_memory_artifact",
        "create_realm",
        "update_realm",
        "delete_realm",
        "save_template",
        "create_template",
        "delete_template",
        "link_template_to_parents",
        "unlink_template_from_parents",
        "create_node_chat_message",
        "create_entities_batch",
        "save_entity",
        "save_entities_batch",
        "delete_entity",
        "create_relations_batch",
        "create_relation",
        "update_relation",
        "delete_relation",
        "create_meta_relation",
        "update_meta_relation",
        "delete_meta_relation",
        "save_entity_fields",
        "delete_entity_fields",
        "save_template_fields",
        "delete_template_fields",
        "create_context_tag_from_object",
        "add_diagram_tag",
        "remove_diagram_tag",
        "add_existing_nodes_to_diagram",
        "create_existing_link_representation",
        "create_diagram",
        "update_diagram",
        "delete_diagram",
    ]
)
RESOURCES = frozenset({"onto://spaces", "onto://user/info"})


class OAuthError(Exception):
    def __init__(self, error="invalid_token", status=401, required=None):
        self.status = status
        self.payload = {"error": error}
        if required:
            self.payload["scope"] = required
        super().__init__(json.dumps(self.payload, separators=(",", ":")))


def dependency_error():
    return OAuthError("dependency_unavailable", 503)


def strict_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError("duplicate member")
            result[key] = item
        return result

    def invalid_constant(_):
        raise ValueError("invalid constant")

    data = json.loads(value, object_pairs_hook=pairs, parse_constant=invalid_constant)
    if not isinstance(data, dict):
        raise TypeError("object required")
    return data


def identity(value):
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(unicodedata.category(c) in {"Cc", "Cs"} for c in value)
    ):
        raise ValueError("invalid identity")
    return value


def integer(value):
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise ValueError("invalid integer")
    return value


def audiences(value):
    items = [value] if isinstance(value, str) else value
    if not isinstance(items, list) or not items:
        raise ValueError("invalid audience")
    if any(not isinstance(v, str) or not v for v in items) or len(set(items)) != len(
        items
    ):
        raise ValueError("invalid audience")
    return frozenset(items)


def scopes(value=""):
    if not isinstance(value, str) or any(
        not (c == " " or 33 <= ord(c) <= 126 and c not in '\\"') for c in value
    ):
        raise ValueError("invalid scope")
    return frozenset(value.split(" ")) - {""}


def provider_session(data):
    values = [identity(data[k]) for k in ("sid", "session_state") if k in data]
    if not values or len(set(values)) != 1:
        raise ValueError("invalid session")
    return values[0]


def forbidden(data):
    # Occurrence, including null or false, is affirmative provenance evidence.
    return bool(MARKERS.intersection(data))


@dataclass(frozen=True)
class OAuthConfig:
    enabled: bool = False
    issuer: str = ""
    resource: str = ""
    audience: str = ""
    allowed_clients: tuple[str, ...] = ()
    exchange_client: str = ""
    exchange_secret: str = field(default="", repr=False)
    core_audience: str = ""

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        enabled = env.get("ONTO_OAUTH_ENABLED", "false").lower()
        if enabled not in {"true", "false"}:
            raise OSError("Invalid OAuth configuration.")
        if enabled == "false":
            return cls()
        try:
            clients = json.loads(env["ONTO_OAUTH_ALLOWED_CLIENT_IDS"])
            if not isinstance(clients, list) or not clients:
                raise ValueError()
            clients = tuple(identity(v) for v in clients)
            if len(set(clients)) != len(clients):
                raise ValueError()
            values = {
                k: identity(env["ONTO_OAUTH_" + v])
                for k, v in {
                    "issuer": "ISSUER",
                    "resource": "RESOURCE",
                    "audience": "AUDIENCE",
                    "exchange_client": "EXCHANGE_CLIENT_ID",
                    "exchange_secret": "EXCHANGE_CLIENT_SECRET",
                    "core_audience": "CORE_AUDIENCE",
                }.items()
            }
            for key in ("issuer", "resource"):
                url = urlsplit(values[key])
                # Validate the URI syntax, including a malformed explicit port.
                port = url.port
                if (
                    not values[key].isascii()
                    or any(c.isspace() for c in values[key])
                    or port == 0
                ):
                    raise ValueError()
                if (
                    url.scheme != "https"
                    or not url.hostname
                    or url.username
                    or url.password
                    or url.query
                    or url.fragment
                ):
                    raise ValueError()
                if key == "resource" and url.path != "/mcp":
                    raise ValueError()
            if values["exchange_client"] in clients:
                raise ValueError()
            return cls(enabled=True, allowed_clients=clients, **values)
        except (KeyError, ValueError, TypeError):
            pass
        raise OSError("Invalid OAuth configuration.")

    @property
    def metadata_url(self):
        u = urlsplit(self.resource)
        return f"{u.scheme}://{u.netloc}/.well-known/oauth-protected-resource/mcp"

    def metadata(self):
        return {
            "resource": self.resource,
            "authorization_servers": [self.issuer],
            "scopes_supported": [READ, WRITE],
        }


@dataclass(frozen=True)
class Claims:
    issuer: str
    subject: str
    client: str
    jti: str
    expires: int
    not_before: int
    session: str
    audience: frozenset[str]
    scope: frozenset[str]

    @property
    def connection_key(self):
        data = json.dumps(
            [self.issuer, self.subject, self.client, self.session],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def valid_at(self, now):
        return self.not_before <= now < self.expires and self.not_before < self.expires


def parse_claims(data):
    if forbidden(data):
        raise OAuthError()
    token_type = identity(data["typ"])
    if token_type != "Bearer":
        # A well-formed non-Bearer provider token is a denial, not an outage.
        if isinstance(data.get("typ"), str) and data["typ"]:
            raise OAuthError()
        raise ValueError("invalid type")
    parsed_scope = scopes(data.get("scope", ""))
    if "offline_access" in parsed_scope:
        raise OAuthError()
    return Claims(
        identity(data["iss"]),
        identity(data["sub"]),
        identity(data["azp"]),
        identity(data["jti"]),
        integer(data["exp"]),
        integer(data.get("nbf", 0)),
        provider_session(data),
        audiences(data["aud"]),
        parsed_scope,
    )


@dataclass
class RequestAuthority:
    service: OAuthService = field(repr=False)
    original: str = field(repr=False)
    claims: Claims
    cancelled: threading.Event = field(default_factory=threading.Event, repr=False)
    required: str = READ
    session_id: str | None = None
    state_store: object = field(default=None, repr=False)
    failure: OAuthError | None = None
    delegated_tokens: list[str] = field(default_factory=list, repr=False)


current_authority: contextvars.ContextVar[RequestAuthority | None] = (
    contextvars.ContextVar("onto_oauth", default=None)
)


class OAuthService:
    def __init__(self, config, *, http=requests, clock=time.time, verify=None):
        self.config, self.http, self.clock = config, http, clock
        self.verify = verify or self._verify_signature
        self._keys = None
        self._keys_until = 0
        self._cache = {}
        self._lock = threading.RLock()
        self.invalidate_connection = lambda key: None

    def _verify_signature(self, token):
        # Discovery can only use the configured authority, never token jku/x5u/iss.
        with self._lock:
            if self._keys is None or self.clock() >= self._keys_until:
                discovery = self._get_json(
                    self.config.issuer.rstrip("/") + "/.well-known/openid-configuration"
                )
                uri = discovery["jwks_uri"]
                target, issuer = urlsplit(uri), urlsplit(self.config.issuer)
                if (
                    discovery["issuer"] != self.config.issuer
                    or target.scheme != "https"
                    or target.netloc != issuer.netloc
                    or target.query
                    or target.fragment
                ):
                    raise dependency_error()
                self._keys = jwt.PyJWKSet.from_dict(self._get_json(uri))
                self._keys_until = self.clock() + 300
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256":
                raise OAuthError()
            matching = [
                k
                for k in self._keys.keys
                if k.key_id == header.get("kid") and k.algorithm_name == "RS256"
            ]
            if len(matching) != 1:
                raise OAuthError()
            jwt.decode(
                token,
                matching[0].key,
                algorithms=["RS256"],
                options={
                    "verify_aud": False,
                    "verify_iss": False,
                    "verify_sub": False,
                    "verify_jti": False,
                    "verify_exp": False,
                    "verify_nbf": False,
                    "verify_iat": False,
                },
            )

    def _get_json(self, url):
        try:
            r = self.http.get(url, timeout=10, allow_redirects=False)
            if r.status_code == 200:
                return strict_json(r.content)
        except Exception:  # noqa: BLE001, S110
            pass
        raise dependency_error()

    def _post(self, suffix, data):
        try:
            r = self.http.post(
                self.config.issuer.rstrip("/") + "/protocol/openid-connect/" + suffix,
                auth=(self.config.exchange_client, self.config.exchange_secret),
                data=data,
                timeout=10,
                allow_redirects=False,
            )
            if r.status_code == 200:
                return strict_json(r.content)
        except Exception:  # noqa: BLE001, S110
            pass
        raise dependency_error()

    def signed(self, token, *, ingress=True):
        try:
            parts = token.split(".")
            if len(parts) != 3 or any(
                not p
                or any(
                    c
                    not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
                    for c in p
                )
                for p in parts
            ):
                raise ValueError()
            header, data = [
                strict_json(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
                for p in parts[:2]
            ]
            if header.get("alg") != "RS256":
                raise ValueError()
            self.verify(token)
            claims = parse_claims(data)
            if claims.issuer != self.config.issuer or not claims.valid_at(self.clock()):
                raise ValueError()
            if ingress and (
                claims.client not in self.config.allowed_clients
                or self.config.audience not in claims.audience
            ):
                raise ValueError()
            return claims
        except OAuthError:
            raise
        except Exception:  # noqa: BLE001, S110
            pass
        raise OAuthError()

    def authenticate(self, token):
        if not self.config.enabled:
            raise OAuthError()
        claims = self.signed(token)
        authority = RequestAuthority(self, token, claims)
        self.authorize(authority, required="")
        return authority

    def authorize(self, authority, required=None):
        if authority.cancelled.is_set():
            raise OAuthError()
        signed = authority.claims
        if not signed.valid_at(self.clock()):
            raise OAuthError()
        data = self._post(
            "token/introspect",
            {"token": authority.original, "token_type_hint": "access_token"},
        )
        if forbidden(data):
            raise OAuthError()
        if type(data.get("active")) is not bool:
            raise dependency_error()
        if not data["active"]:
            self.evict(signed.connection_key)
            try:
                self.invalidate_connection(signed.connection_key)
            except OAuthError:
                # The store has marked itself unavailable. Inactive provider
                # authorization remains an invalid-token denial on this call.
                self.evict(signed.connection_key)
            raise OAuthError()
        try:
            returned = parse_claims(data)
            client = identity(data["client_id"])
            token_type = identity(data["token_type"])
        except OAuthError:
            raise
        except (KeyError, ValueError, TypeError):
            raise dependency_error() from None
        if token_type != "Bearer":
            raise OAuthError()
        # Missing returned nbf is permitted, but present nbf must match.
        if "nbf" not in data:
            from dataclasses import replace

            returned = replace(returned, not_before=signed.not_before)
        if (
            returned != signed
            or client != signed.client
            or not signed.valid_at(self.clock())
            or authority.cancelled.is_set()
        ):
            raise OAuthError()
        required = authority.required if required is None else required
        if not set(required.split()).issubset(signed.scope):
            raise OAuthError("insufficient_scope", 403, required)

    def evict(self, key):
        with self._lock:
            self._cache.pop(key, None)

    def cache_owners(self):
        """Bound idle caches and let storage purge entries removed by MongoDB TTL."""
        with self._lock:
            now = self.clock()
            self._cache = {
                key: entry for key, entry in self._cache.items() if entry[1] > now
            }
            return tuple(self._cache)

    def exchange(self, authority):
        """Return the selected token and its immutable final-send deadline."""
        key = authority.claims.connection_key
        with self._lock:
            # Bound both stale entry residency and renewal's actual original expiry.
            now = self.clock()
            self._cache = {k: v for k, v in self._cache.items() if v[1] > now}
            cached = self._cache.get(key)
            if cached and now < min(cached[1], authority.claims.expires):
                return cached[0], min(cached[1], authority.claims.expires)
            data = self._post(
                "token",
                {
                    "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                    "subject_token": authority.original,
                    "subject_token_type": ACCESS_TOKEN,
                    "requested_token_type": ACCESS_TOKEN,
                    "audience": self.config.core_audience,
                },
            )
            try:
                token = identity(data["access_token"])
                # Keycloak 24's legacy exchange omits issued_token_type. We
                # explicitly request an access token and still verify the
                # Bearer response and signed JWT below; a contradictory
                # present value (including null) must fail closed.
                if data["token_type"] != "Bearer" or (
                    "issued_token_type" in data
                    and data["issued_token_type"] != ACCESS_TOKEN
                ):
                    raise ValueError()
                claims = self.signed(token, ingress=False)
                original = authority.claims
                if (
                    claims.subject != original.subject
                    or claims.session != original.session
                    or claims.client != self.config.exchange_client
                    or self.config.core_audience not in claims.audience
                ):
                    raise ValueError()
                until = min(original.expires, claims.expires, self.clock() + 300)
                self._cache[key] = (token, until)
                return token, until
            except Exception:  # noqa: BLE001, S110
                pass
        raise dependency_error()

    def credentials(self):
        authority = current_authority.get()
        values = [self.config.exchange_secret]
        if authority:
            values.append(authority.original)
            values.extend(authority.delegated_tokens)
        with self._lock:
            values += [v[0] for v in self._cache.values()]
        return tuple(v for v in values if v)


def required_scopes(name):
    if name in READ_TOOLS or name in RESOURCES:
        return READ
    if name in WRITE_TOOLS:
        return READ + " " + WRITE
    raise OAuthError("insufficient_scope", 403, READ + " " + WRITE)


def authorize_registered(name):
    authority = current_authority.get()
    if authority:
        authority.required = required_scopes(name)
        authority.service.authorize(authority)
        if authority.state_store is not None:
            authority.state_store.require(
                authority.session_id, authority.claims.connection_key
            )


def tool_error(exc):
    from fastmcp.exceptions import ToolError

    return ToolError(str(exc))
