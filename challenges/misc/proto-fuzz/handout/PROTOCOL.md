# FZLP/1 -- Fictional Zoned Line Provisioning (partial note)

Internal note, recovered from a wiki. Incomplete. Describes intended behaviour
only; treat edge cases as unspecified.

## Framing

- Line-oriented over TCP. Each request is one line terminated by `\n` (`\r\n`
  also accepted).
- On connect the server sends a banner line: `FZLP/1 ready`.
- Verbs are case-insensitive. Tokens are whitespace-separated.

## Verbs

| Verb        | Meaning                                                        |
|-------------|----------------------------------------------------------------|
| `PING`      | Liveness. Replies `PONG`.                                      |
| `STAT`      | Reports the state of the channels and a summary `mask`.        |
| `HELP`      | Lists the verbs the server currently offers.                   |
| `CFG <n>`   | Provisions channels. See below.                                |

## Channels

The device exposes **3 provisionable channels**, numbered `0`, `1`, `2`. Each
channel holds one byte (`00`..`ff`). `STAT` reports each channel and a `mask`
whose bit *k* is set when channel *k* is non-zero.

> `reserved_admin_ch` in `STAT` output is a hardware constant. Not
> provisionable from this protocol.

## CFG

    CFG <n>
    <entry 0>
    <entry 1>
    ...

`<n>` is the number of channels to configure; **valid range `0..3`**. After the
header line the server reads `<n>` entry lines. Entry line *k* is the new value
for channel *k*, given as **two hex digits** (e.g. `01`, `ff`). The server
replies `OK mask=0x..` with the resulting mask.

Example (configure channels 0 and 1):

    CFG 2
    01
    01
    -> OK mask=0x03

## Notes / TODO

- (TODO) tighten entry validation -- non-hex entries currently coerce to `00`.
- (TODO) the maintenance path (`DUMP`) is disabled in the field build; it stays
  locked unless the maintenance channel is armed. Arming it from this protocol
  was supposed to be impossible after we dropped channel 3 from the docs. Double
  check the entry loop bound before shipping.
