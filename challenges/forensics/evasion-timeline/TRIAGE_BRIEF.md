# IR-2024-1147 — Host triage brief

**Host:** `FIN-WIN11-07.corp.northwind.internal` (finance workstation)
**Window:** 2024-11-05 08:12 – 08:47 UTC (host telemetry export)
**Artifact:** `sysmon.jsonl` — Sysmon "Operational" events, one JSON object per
line, exported from the endpoint's event channel.

## Background

The SOC opened this ticket after the EDR *quarantine* action failed to fire on
this host during an alert storm, yet a follow-up threat hunt found a stray
autorun and an outbound connection to a low-reputation address. The analyst who
triaged it wrote:

> "The process tree looks clean at a glance — everything traces back to normal
> Windows parents. But the alert correlation and the follow-on activity don't
> line up with the parentage the telemetry is claiming. Something walked in
> under cover of a trusted process and the ancestry it presented is a lie.
> I ran out of shift; handing off the raw export."

## Your job

Work the telemetry and reconstruct **what evaded detection**. Do not trust
process names or paths at face value — verify the relationships between events
against the clock. Identify the one process whose recorded lineage cannot be
true, pull the indicator it is hiding, and report it.

## Field reference (Sysmon)

* `EventID` 1 = Process create, 5 = Process terminate, 3 = Network connect,
  7 = Image load, 11 = File create, 13 = Registry set, 22 = DNS query.
* Process-create events carry `ProcessGuid`/`ProcessId` and the
  `ParentProcessGuid`/`ParentProcessId`/`ParentImage` they were launched with.
* `UtcTime` is the event time; process-terminate events share the terminated
  process's `ProcessGuid`.

## Deliverable

The indicator you recover is wrapped as `NCTF{...}` (lowercase letters, digits
and underscores). Submit that string.

> Note: more than one process on this host was launched with an obfuscated,
> encoded command line, and not all of them are hostile — admins encode
> commands too. Decide which process is the intruder from the evidence, not
> from the fact that its command line is encoded.
