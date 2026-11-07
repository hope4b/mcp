"""Non-secret authorization configuration deliverable, not a runtime validator.

The authorization owner must apply and verify these represented prerequisites
on the actual provider before enabling OAuth. No provider writes occur here.
"""

from .oauth import READ, WRITE


def represented_policy(config):
    notes = [
        ("IMPERSONATOR_ID", "onto_impersonator_id"),
        ("IMPERSONATOR_USERNAME", "onto_impersonator_username"),
        ("IMPERSONATOR_CLIENT", "onto_impersonator_client"),
    ]
    clients = []
    for client_id in config.allowed_clients:
        clients.append(
            {
                "clientId": client_id,
                "consentRequired": True,
                "standardFlowEnabled": True,
                "implicitFlowEnabled": False,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
                "attributes": {
                    "pkce.code.challenge.method": "S256",
                    "access.token.lifespan": "300",
                    "client.session.idle.timeout": "1800",
                    "client.session.max.lifespan": "28800",
                },
                "protocolMappers": [
                    {
                        "name": claim,
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-usersessionmodel-note-mapper",
                        "config": {
                            "user.session.note": note,
                            "claim.name": claim,
                            "jsonType.label": "String",
                            "access.token.claim": "true",
                            "introspection.token.claim": "true",
                            "id.token.claim": "false",
                        },
                    }
                    for note, claim in notes
                ],
            }
        )
    clients.append(
        {
            "clientId": config.core_audience,
            "consentRequired": False,
            "standardFlowEnabled": False,
            "implicitFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": False,
        }
    )
    return {
        "basis": "Keycloak 24.0.1; separately applied and verified authorization prerequisites",
        "bindings": {
            "issuer": "ONTO_OAUTH_ISSUER",
            "external_clients": "ONTO_OAUTH_ALLOWED_CLIENT_IDS",
            "exchange_client": "ONTO_OAUTH_EXCHANGE_CLIENT_ID",
            "core_target": "ONTO_OAUTH_CORE_AUDIENCE",
        },
        "clients": clients,
        "exchange": {
            "clientId": config.exchange_client,
            "target": config.core_audience,
            "authentication": "client_secret_basic",
            "subject_preserving_only": True,
            "requested_subject_permitted": False,
            "ingress_allowed": False,
        },
        "consent_scopes": {
            "independent_read": READ,
            "separately_consented_write": WRITE,
            "write_default_grant": False,
        },
        "external_registration_requirements": {
            "callbacks": "Each registration owns exact callbacks and confidential-client authentication.",
            "offline_access": "Exclude from both default and optional grants.",
            "authority": "No impersonation or token-exchange permissions for external clients.",
            "transition": "Invalidate outstanding authorization from earlier unrestricted configurations before admission.",
            "mappers": "All three direct client mappers are nonoptional and preserved through introspection.",
            "audience": "Configure ingress ONTO_OAUTH_AUDIENCE; fixed-audience host compatibility is unverified.",
        },
        "storage_policy": {
            "transport_encryption": "TLS with server identity verification",
            "storage_encryption": "required",
            "restricted_runtime_access": "required",
            "backup_encryption": "required",
            "backup_retention_seconds": 604800,
        },
    }
