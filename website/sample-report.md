# LazyRemote Network Fit Review — project-owned sample

Date: 9 September 2026  
Scope: one synthetic Linux workstation behind CGNAT, one existing relay, and two owner-operated clients

> This is not a customer result. The names, addresses, ports, and findings are synthetic. The structure shows the report a buyer receives; it contains no private fleet data.

## Decision

**Conditional go.** The route is a reasonable fit if every reverse listener remains on relay loopback, the tunnel and jump roles use separate restricted identities, host keys are pinned, and an independent administrator path survives the test. Do not deploy if any of those gates cannot be met.

## Stated need and existing pieces

The owner needs SSH and a private browser viewer from a laptop and phone to a home Linux workstation behind CGNAT. An owner-controlled relay already accepts public SSH. The workstation can make outbound SSH connections. Hardware and relay hosting are outside this review.

## Proposed route

`owner-controlled client → authenticated, pinned relay SSH → relay loopback reverse listener → workstation loopback service`

The route is end-to-end SSH through reviewed identities. A successful carrier alone does not authorize a user, and a browser viewer does not become public merely because the relay is public.

## Listener exposure map

| Boundary | Intended bind | Who can reach it | Decision |
|---|---|---|---|
| Relay SSH | Reviewed public address | Approved SSH clients | Conditional |
| Reverse listener | `127.0.0.1` on relay | Relay-local jump path only | Required |
| Endpoint controller | `127.0.0.1` on workstation | Local app or declared forward | Required |
| Private browser viewer | `127.0.0.1` on workstation | Its dedicated reviewed forward | Required |
| Raw VNC / RDP | No public listener | No Internet source | Stop if exposed |

These are illustrative labels, not port recommendations. A paid report records observed bind addresses and listener owners without copying secrets.

## Identity and trust map

- **Relay administrator:** independent recovery only; not the everyday jump or tunnel identity.
- **Tunnel identity:** no shell, TTY, X11, agent forwarding, wildcard listener, or arbitrary target.
- **Jump identity:** separate client key and pinned relay host key; access ends at declared loopback routes.
- **Endpoint identity:** separate host identity and permissions for each enrolled computer.

## Findings

1. **Stop — wildcard reverse listening.** If the relay shows a reverse listener on `0.0.0.0` or `::`, stop the candidate and correct the SSH policy before any client test.
2. **Required — role separation.** Do not reuse the relay administrator key for the persistent carrier or everyday client access.
3. **Required — host verification.** Pin relay and endpoint host identities. A changed fingerprint fails closed and requires an independent check.
4. **Open — reboot recovery.** A running service is not reboot evidence. Prove one controlled restart and one authorized reboot before calling persistence verified.

## Acceptance checklist

- [ ] Every service and reverse listener has a named owner and intended bind address.
- [ ] Missing, wrong, revoked, and changed identities fail closed.
- [ ] SSH and the private viewer work through their declared routes; raw desktop ports remain unreachable.
- [ ] Stopping the carrier removes the relay loopback route and produces a bounded failure.
- [ ] Restarting one component does not start a duplicate listener or disturb another remote-access service.
- [ ] The independent administrator path and exact rollback steps were tested.

## Rollback order

1. Close the client session.
2. Stop only the candidate carrier.
3. Confirm its relay loopback listener is gone.
4. Restore the reviewed prior unit or configuration.
5. Re-probe the existing path.

## Free fit check

Send the endpoint operating systems, whether a reachable relay already exists, the NAT or port constraint, the intended access path, and whether ownership and network-policy permission are confirmed. Do not send passwords, private keys, access codes, or unredacted configuration.

The fixed USD 250 review is software-only for one reachable relay and up to three existing buyer-owned computers. Deployment, hardware, relay hosting, router or firewall changes, wake-on-LAN, desktop capture, ongoing support, and unseen-topology connectivity guarantees are outside scope.

Review the exact offer: <https://remote.lazying.art/#review>
