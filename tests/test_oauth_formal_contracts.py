"""Independent formal oracles and inert DTO boundaries; no provider operations."""

import asyncio
import copy
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from test_oauth_authorization import CONFIG, EXPECTED_WRITE

from onto_mcp import api_resources as api
from onto_mcp import oauth_http
from onto_mcp.oauth_policy import represented_policy

# Explicit approved note/claim pairs, not generated from the deliverable.
MAPPINGS = {
    "IMPERSONATOR_ID": "onto_impersonator_id",
    "IMPERSONATOR_USERNAME": "onto_impersonator_username",
    "IMPERSONATOR_CLIENT": "onto_impersonator_client",
}


def inspect_issuance(policy):
    findings = []
    for client in policy["clients"]:
        if client["clientId"] not in CONFIG.allowed_clients:
            continue
        if client.get("serviceAccountsEnabled") is not False:
            findings.append("service issuance")
        mappings = client.get("protocolMappers", [])
        actual = {
            m["config"]["user.session.note"]: m["config"]["claim.name"]
            for m in mappings
        }
        if actual != MAPPINGS or len(mappings) != 3:
            findings.append("mandatory mappings")
        for mapper in mappings:
            c = mapper["config"]
            if (
                mapper["protocolMapper"] != "oidc-usersessionmodel-note-mapper"
                or c.get("jsonType.label") != "String"
                or c.get("access.token.claim") != "true"
                or c.get("introspection.token.claim") != "true"
            ):
                findings.append("mapper inclusion")
    return findings


@pytest.mark.parametrize("fault", ["service", *MAPPINGS])
def test_issuance_inspection_rejects_nonconforming_samples(fault):
    policy = represented_policy(CONFIG)
    assert inspect_issuance(policy) == []
    sample = copy.deepcopy(policy)
    client = sample["clients"][0]
    if fault == "service":
        client["serviceAccountsEnabled"] = True
    else:
        client["protocolMappers"] = [
            m
            for m in client["protocolMappers"]
            if m["config"]["user.session.note"] != fault
        ]
    assert inspect_issuance(sample) == [
        "service issuance" if fault == "service" else "mandatory mappings"
    ]
    assert inspect_issuance(policy) == []


def inspect_storage(policy):
    s = policy["storage_policy"]
    return (
        s.get("transport_encryption") == "TLS with server identity verification"
        and all(
            s.get(k) == "required"
            for k in [
                "storage_encryption",
                "restricted_runtime_access",
                "backup_encryption",
            ]
        )
        and type(s.get("backup_retention_seconds")) is int
        and 0 <= s["backup_retention_seconds"] <= 604800
    )


@pytest.mark.parametrize(
    "fault",
    [
        "retention",
        "transport_encryption",
        "storage_encryption",
        "restricted_runtime_access",
        "backup_encryption",
    ],
)
def test_represented_storage_encryption_access_and_seven_day_bound(fault):
    policy = represented_policy(CONFIG)
    assert inspect_storage(policy)
    sample = copy.deepcopy(policy)
    sample["storage_policy"][
        "backup_retention_seconds" if fault == "retention" else fault
    ] = 604801 if fault == "retention" else "unverified"
    assert not inspect_storage(sample)


SELECTION = [
    "actual authorized results",
    "identifiable choices",
    "stable IDs",
    "distinguishing context",
    "ask and wait",
    "Never select by list order, last-used realm, or fabricated IDs",
    "Clarify vague replies again",
    "Cancellation ends the request",
    "A changed realm invalidates prior targets",
    "resolve them again",
    "Explicit identified multiple-target requests are not ambiguity",
    "resolved realm and targets visible before mutation",
    "neither write consent nor backend permission",
    "First use may provision an Onto user and personal realm, even with read-only consent",
]
CONFIRMATION = [
    "Ordinary explicitly instructed editing needs no",
    "confirmation",
    "Before deletion, clearing",
    "replacement losing prior content",
    "explain the known action and targets",
    "additional conversational confirmation",
    "wait before invoking",
    "material changes require fresh confirmation",
    "Save/upsert defaults and helper replacement can lose prior content under existing semantics",
    "MCP cannot prove human receipt or confirmation",
]


def normalized(text):
    return " ".join(text.split())


def assert_passages(text, passages):
    text = normalized(text)
    for passage in passages:
        assert passage in text, passage


def inspect_safety_description(text):
    text = normalized(text).lower()
    prohibited = [
        "server-attested human consent",
        "server verifies human confirmation",
        "pending-confirmation",
        "pending_confirmation",
    ]
    return not any(p in text for p in prohibited)


def test_complete_guidance_across_delivered_surfaces():
    from onto_mcp.connector_guidance import CONNECTOR_GUIDANCE

    howto = json.dumps(api.how_to_use_onto_mcp())
    for text in [api.mcp.instructions, howto]:
        # JSON escapes are irrelevant to the oracle; how-to safety notes carry text.
        if text == howto:
            text = " ".join(api.how_to_use_onto_mcp()["safety_notes"])
        assert_passages(text, SELECTION + CONFIRMATION)
        assert "Cancellation prevents invocation" in normalized(text)
    assert_passages(CONNECTOR_GUIDANCE, SELECTION)

    async def descriptions():
        return {
            name: (await api.mcp.get_tool(name)).description for name in EXPECTED_WRITE
        }

    for name, description in asyncio.run(descriptions()).items():
        assert_passages(description, CONFIRMATION)
        assert "Cancellation stops invocation" in normalized(description), name
        assert "grounded, resolved realm and targets" in description, name
        assert inspect_safety_description(description)
        assert not inspect_safety_description(
            description + " The server verifies human confirmation."
        )
        assert not inspect_safety_description(
            description + " Returns pending_confirmation."
        )
        assert not inspect_safety_description(
            description + " Provides server-attested human consent."
        )


def test_configured_client_revocation_instructions():
    for text in [
        api.mcp.instructions,
        " ".join(api.how_to_use_onto_mcp()["safety_notes"]),
    ]:
        assert_passages(
            text,
            [
                "Each configured external OAuth client owns renewal and its refresh token",
                "that client's actual consent entry",
                "configured issuer's Keycloak Account Console",
                "use remove access",
                "Example application labels are not mandatory names",
                "{configured issuer}/protocol/openid-connect/revoke",
                "its own configured authentication, refresh token, and token_type_hint=refresh_token",
                "MCP never holds that refresh token",
                "HTTP 200 proves neither prior grant existence/absence nor effective revocation",
                "fresh introspection of an outstanding original access token returning active=false",
                "New dispatch then stops despite caches",
                "already dispatched work may finish",
                "User/client-wide revocation differs from jti revocation",
                "provider session identity is not device identity",
                "ChatGPT Disconnect behavior remains unverified",
            ],
        )


@pytest.fixture
def downstream():
    """Intercept the actual request boundary; response body is an independent fixture."""
    with (
        patch.object(api, "ONTO_API_BASE", "https://core.test/api"),
        patch.object(api, "ONTO_API_KEY", "inert-key"),
        patch.object(api, "IS_HTTP_TRANSPORT", False),
        patch.object(api.requests, "request") as send,
    ):
        response = SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=dict,
            text="{}",
            content=b"{}",
        )
        send.return_value = response
        yield send, response


def test_real_identity_projections_with_inert_current_user(downstream):
    send, response = downstream
    user = {
        "id": "user-u",
        "name": "User",
        "custom": {"kept": True},
        "userRealmsRoles": [
            {"realmId": "r1", "realmName": "Same", "role": "OWNER"},
            {"realmId": "r2", "realmName": "Same", "role": "READER"},
        ],
    }
    response.json = lambda: copy.deepcopy(user)
    assert api.get_user_info() == user
    assert api.get_user_spaces() == [
        {"id": "r1", "name": "Same"},
        {"id": "r2", "name": "Same"},
    ]
    assert (
        api.list_available_realms()
        == "Available realms (2):\n\n1. Same\n   ID: r1\n\n2. Same\n   ID: r2\n"
    )
    assert len(send.call_args_list) == 3
    assert all(
        c.args == ("GET", "https://core.test/api/user/v2/current")
        for c in send.call_args_list
    )


@pytest.mark.parametrize(
    "tool,provided",
    [("save_template", False), ("save_template", True), ("create_template", False)],
)
def test_template_payload_generation_and_native_projection(downstream, provided, tool):
    send, response = downstream
    response.json = lambda: {"id": "returned", "name": "Native", "comment": "from Core"}
    args = {"realm_id": "r", "name": " Input "}
    if provided:
        args.update(template_id=" supplied ", comment="given")
    with patch.object(api.uuid, "uuid4", return_value="generated"):
        result = getattr(api, tool)(**args)
    assert send.call_args.args == ("POST", "https://core.test/api/realm/r/meta")
    assert send.call_args.kwargs["json"] == {
        "id": "supplied" if provided else "generated",
        "name": "Input",
        "comment": "given" if provided else "",
    }
    assert (
        result
        == (
            "Template updated successfully."
            if provided
            else "Template created successfully."
        )
        + "\nID: returned\nName: Native\nComment: from Core"
    )
    send.assert_called_once()


@pytest.mark.parametrize("provided", [False, True])
def test_entity_defaults_classification_omission_and_native_projection(
    downstream, provided
):
    send, response = downstream
    response.json = lambda: {
        "uuid": "native",
        "name": "Returned",
        "comment": "Core comment",
    }
    args = {"realm_id": " r ", "name": " Input "}
    if provided:
        args.update(entity_id=" e ", meta_entity_id=" t ", comment="supplied")
    result = api.save_entity(**args)
    assert send.call_args.args == ("POST", "https://core.test/api/realm/r/entity")
    assert send.call_args.kwargs["json"] == (
        {"id": "e", "metaEntityId": "t", "name": "Input", "comment": "supplied"}
        if provided
        else {"name": "Input", "comment": ""}
    )
    assert result == (
        ("Entity updated successfully." if provided else "Entity created successfully.")
        + "\nID: native\nName: Returned\nComment: Core comment"
        + (
            ""
            if provided
            else "\nMeta entity: omitted from request; Onto may remove current classification."
        )
    )
    send.assert_called_once()


def test_entity_batch_payload_and_created_entities_projection(downstream):
    send, response = downstream
    response.json = lambda: {
        "createdEntities": [
            {
                "uuid": "n1",
                "name": "Native",
                "comment": "Core",
                "metaEntity": {"id": "t", "name": "Type"},
            }
        ]
    }
    result = api.save_entities_batch(
        "r",
        [
            {"name": " First "},
            {
                "name": " Second ",
                "id": " e ",
                "meta_entity_id": " t ",
                "comment": "given",
            },
            {"name": "Third", "id": None, "metaEntityId": "t2"},
        ],
    )
    assert send.call_args.args == ("POST", "https://core.test/api/realm/r/entity/batch")
    assert send.call_args.kwargs["json"] == {
        "entities": [
            {"name": "First", "comment": ""},
            {"name": "Second", "comment": "given", "id": "e", "metaEntityId": "t"},
            {"name": "Third", "comment": "", "metaEntityId": "t2"},
        ]
    }
    assert (
        result
        == "Successfully saved 1 entities in realm r.\n\n1. Native\n   UUID: n1\n   Comment: Core\n   Template: Type (t)\n"
    )
    send.assert_called_once()


@pytest.mark.parametrize("name", ["", " Name "])
def test_delete_parameters_preserved(downstream, name):
    send, _ = downstream
    api.delete_template(" r ", " t ")
    assert send.call_args.args == ("DELETE", "https://core.test/api/realm/r/meta")
    assert send.call_args.kwargs["params"] == {"id": "t"}
    send.reset_mock()
    api.delete_entity(" r ", [" e1 ", "", "e2"], name=name)
    assert send.call_args.args == ("DELETE", "https://core.test/api/realm/r/entity")
    assert send.call_args.kwargs["params"] == dict(
        ids=["e1", "e2"], **({"name": "Name"} if name else {})
    )
    send.assert_called_once()


def test_unconditional_maintenance_without_traffic_and_shutdown():
    async def exercise():
        events = []
        sleepers = asyncio.Queue()
        release = asyncio.Queue()
        real_sleep = asyncio.sleep

        async def sleep(interval):
            events.append(("interval", interval))
            await sleepers.put(True)
            await release.get()

        def sweep():
            events.append(("sweep", None))
            return False

        @asynccontextmanager
        async def lifespan(app):
            yield

        key = SimpleNamespace(router=SimpleNamespace(lifespan_context=lifespan))
        oauth = SimpleNamespace(router=SimpleNamespace(lifespan_context=lifespan))
        mcp = SimpleNamespace(http_app=lambda **kw: oauth)
        with (
            patch.object(oauth_http.OAuthConfig, "from_env", return_value=CONFIG),
            patch.object(oauth_http, "OAuthService"),
            patch.object(
                oauth_http,
                "configured_store",
                return_value=SimpleNamespace(sweep=sweep),
            ),
            patch.object(oauth_http.asyncio, "sleep", side_effect=sleep),
        ):
            app = oauth_http.build_dual_app(mcp, key)
            async with key.router.lifespan_context(key):
                assert events == [("sweep", None)]  # readiness cleanup precedes serving
                await sleepers.get()
                for _ in range(2):
                    await release.put(True)
                    await sleepers.get()
                assert len([e for e in events if e[0] == "sweep"]) == 3
                assert all(
                    0 < interval <= 60
                    for kind, interval in events
                    if kind == "interval"
                )
                assert app.key_app is key  # no HTTP call/traffic was needed
            stopped = list(events)
            await real_sleep(0)
            assert events == stopped
            assert not [
                t
                for t in asyncio.all_tasks()
                if t is not asyncio.current_task() and not t.done()
            ]

    asyncio.run(exercise())
