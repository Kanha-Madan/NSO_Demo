# NSO_Demo — L3VPN Service Package for Cisco NSO (IOS-XR)

My first Cisco NSO project: a service package that turns a handful of customer
inputs into a complete L3VPN configuration on an IOS-XR PE router — VRF, QoS
policy-maps, QinQ sub-interface and BGP VRF — and pushes it to the device.

---

## 1. What this repo does

### The problem statement

The instructor provided a reference ("golden") IOS-XR configuration for one
customer (`VRF config.docx`) with the per-customer values highlighted in red,
and asked to:

1. Create a **service package** (YANG + template).
2. Make the red values **variables** (service inputs).
3. **Push the config to the device** through NSO.

The configuration has four parts:

| Part | What it configures |
|---|---|
| VRF | `vrf <name>`, IPv4/IPv6 unicast, import/export route-targets, `maximum prefix` |
| QoS | Ingress `policy-map` (police with burst/peak-burst, set MPLS EXP) and egress `policy-map` (shape) |
| Interface | QinQ sub-interface: description, bandwidth, `dot1q`/`second-dot1q`, service-policies, VRF, IPv4/IPv6 addresses, uRPF, unreachables |
| Routing | `router bgp 9730` → `vrf <name>` with RD, label mode per-vrf, dampening, redistribute connected/static |

### What has been achieved

- NSO **6.6.1** installed locally on macOS (Apple Silicon) with the **cisco-iosxr-cli-7.74** NED.
- A lab with two simulated IOS-XR routers (**netsim** `pe0`, `pe1`).
- The NED's real data structure captured from a device (`output/pe1-captured.xml`) and used to build correct templates.
- Service package **`l3vpn-service`** (YANG + Python + 4 XML templates) built and loaded (`packages reload` → `result true`).
- A service instance deployed to `pe0`; `commit dry-run outformat native` output **matches the instructor's configuration line by line**.
- Python derives values automatically: rate = bandwidth × 1000, burst and peak-burst.

---

## 2. How it works

```
 You type ~15 values                    NSO does the rest
 ─────────────────────                  ─────────────────────────────────────────────
 l3vpn-service MSHA-...        ──►  YANG model      validates input (types, ranges, must/when)
   device-name pe0                       │
   bandwidth 1676                        ▼
   vrf vrf-name MSHA-ML-M           Python (main.py) calculates derived values
   ...                                   │   rate = 1676*1000 = 1676000 bps
                                         │   burst = rate*1.5/8 = 314250 bytes
                                         │   peak  = 2*burst  = 628500 bytes
                                         ▼
                                    4 XML templates map inputs → NED data model
                                         │   l3vpn-vrf / l3vpn-qos / l3vpn-interface / l3vpn-bgp
                                         ▼
                                    IOS-XR NED renders device CLI and sends it to pe0
```

Because NSO services use **FASTMAP**, only the *create* logic is written.
NSO automatically works out **modify** (sends only the diff) and **delete**
(removes exactly what the service created).

---

## 3. Repository layout

```
NSO_Demo/
├── README.md                          ← this file
├── VRF config.docx                    ← instructor's problem statement
├── .vscode/settings.json              ← lets VS Code find NSO's Python library (optional)
├── scripts/
│   ├── env.sh                         ← load NSO into the terminal (source it)
│   ├── start-lab.sh                   ← start routers + NSO, fetch keys, sync
│   └── stop-lab.sh                    ← stop NSO + routers cleanly
├── device-sample-config/
│   └── instructor-sample.cfg          ← instructor config in real IOS-XR syntax
├── output/
│   └── pe1-captured.xml               ← NED XML captured from pe1 (template reference)
└── nso/
    ├── installers/                    ← NSO + NED installer files
    ├── nso661/                        ← NSO 6.6.1 local install (do not move!)
    ├── current -> nso661              ← symlink used by env.sh
    ├── neds/cisco-iosxr-cli-7.74/     ← IOS-XR NED package
    ├── netsim/                        ← simulated routers pe0, pe1
    └── ncs-run/                       ← NSO runtime directory
        ├── ncs.conf                   ← NSO configuration
        ├── ncs-cdb/                   ← NSO database (devices, services, configs)
        ├── logs/                      ← ncs.log, devel.log, python VM logs
        └── packages/
            ├── cisco-iosxr-cli-7.74 -> ../../neds/...
            └── l3vpn-service/         ← ★ THE SERVICE PACKAGE
                ├── package-meta-data.xml
                ├── src/Makefile
                ├── src/yang/l3vpn-service.yang
                ├── python/l3vpn_service/main.py
                └── templates/
                    ├── l3vpn-vrf.xml
                    ├── l3vpn-qos.xml
                    ├── l3vpn-interface.xml
                    └── l3vpn-bgp.xml
```

> ⚠️ The service package lives **inside** `nso/ncs-run/packages/`. Never
> delete or re-create `ncs-run` without first copying `l3vpn-service/`
> somewhere safe.

---

## 4. Service inputs

| Input | Mandatory | Default | Example | Used in |
|---|---|---|---|---|
| `name` (key) | yes | – | `MSHA-ML3-1-810095` | service instance id |
| `device-name` | yes | – | `pe0` | target router |
| `ipv6-enable` | no | `true` | `true` | all IPv6 blocks |
| `bgp-as` | no | `9730` | `9730` | `router bgp`, RD, RTs |
| `bandwidth` (kbps) | yes | – | `1676` | interface bandwidth, QoS rates |
| `vrf vrf-name` | yes | – | `MSHA-ML-M` | VRF, interface, BGP |
| `vrf rd-value` | yes | – | `71728651` | `rd <bgp-as>:<rd-value>` |
| `vrf route-target <rt-value>` (list, ≥1) | yes | direction `both` | `71728651` | import/export RTs |
| `vrf maximum-prefix limit` / `threshold` | no | `20000` / `80` | – | `maximum prefix` |
| `qos in-policy-name` | yes | – | `in_STANDARD_ETH_1676_By_NSO` | ingress policy-map |
| `qos out-policy-name` | yes | – | `out_STANDARD_ETH_1676_By_NSO` | egress policy-map |
| `qos mpls-exp` | no | `0` | `0` | `set mpls experimental imposition` |
| `qos burst` / `peak-burst` | no | calculated | – | optional manual override |
| `interface interface-type` | yes | – | `GigabitEthernet` | sub-interface type |
| `interface interface-id` | yes | – | `0/0/1` | parent interface |
| `interface subintf-id` | yes | – | `5002` | `.5002` |
| `interface description` | no | – | `MSHA-ML3-1-...` | description |
| `interface svlan` / `cvlan` | yes | – | `3714` / `1260` | `dot1q ... second-dot1q ...` |
| `interface ip-address` / `subnet-mask` | yes | – | `52.45.120.133` / `255.255.255.252` | IPv4 address |
| `interface ipv6-address` | when IPv6 on | – | `5936:3532::1/126` | IPv6 address |

**Derived in Python (`main.py`):**

| Variable | Formula | 1676 kbps → |
|---|---|---|
| `POLICE_RATE_BPS`, `SHAPE_RATE_BPS` | `bandwidth × 1000` | `1676000` |
| `BURST_BYTES` | `rate × 1.5 / 8` (Cisco 1.5 s rule) | `314250` |
| `PEAK_BURST_BYTES` | `2 × burst` | `628500` |
| `INTF_ID` | `interface-id + "." + subintf-id` | `0/0/1.5002` |

---

## 5. Prerequisites

| Item | Version used | Notes |
|---|---|---|
| macOS | Apple Silicon (arm64) | |
| NSO | **6.6.1** `nso-6.6.1.darwin.arm64.installer.bin` | from Cisco DevNet / software.cisco.com |
| NED | **cisco-iosxr-cli-7.74.11** `ncs-6.6.1-cisco-iosxr-7.74.11.signed.bin` | first number in file name must match NSO version |
| Java | 17 | `brew install openjdk@17` |
| Python | 3.x (NSO 6.6.1 is built against 3.11) | if the Python VM fails, use `brew install python@3.11` |
| VS Code extensions | YANG (TypeFox), Python, XML (Red Hat) | optional, for editing |

**Golden rules learned along the way**

- **Never install NSO in a path containing spaces** — NSO scripts break.
- **Never move an NSO local install** after installing — `ncsrc` contains the absolute path. Re-install instead.
- **Every new terminal** needs: `cd ~/Projects/NSO_Demo && source scripts/env.sh`.

---

## 6. First-time setup (from scratch)

Each block states the directory it must be run from (📁).

### 6.1 Create folders and copy installers

```bash
# 📁 anywhere
mkdir -p ~/Projects/NSO_Demo/{scripts,device-sample-config,output,nso/installers,nso/neds}
cp <download-location>/nso-6.6.1.darwin.arm64.installer.bin \
   <download-location>/ncs-6.6.1-cisco-iosxr-7.74.11.signed.bin \
   ~/Projects/NSO_Demo/nso/installers/
```

### 6.2 Install NSO and unpack the NED

```bash
# 📁 ~/Projects/NSO_Demo/nso/installers
cd ~/Projects/NSO_Demo/nso/installers
sh nso-6.6.1.darwin.arm64.installer.bin --local-install ../nso661    # install NSO
cd .. && ln -sfn nso661 current                                    # version-independent symlink
cd installers
sh ncs-6.6.1-cisco-iosxr-7.74.11.signed.bin                         # verify Cisco signature + unpack
tar -xzf ncs-6.6.1-cisco-iosxr-7.74.11.tar.gz -C ../neds           # x=extract z=gunzip f=file
ls ../neds                                                         # → cisco-iosxr-cli-7.74
```

- `--local-install` = install into one folder as your user (development mode).
- The `.signed.bin` verifies the file against Cisco's certificate chain before unpacking.

### 6.3 Create `scripts/env.sh`

```bash
# Usage:  source scripts/env.sh
if [ -n "${ZSH_VERSION:-}" ]; then _src="${(%):-%x}"; else _src="${BASH_SOURCE[0]}"; fi
export NSO_DEMO="$(cd "$(dirname "$_src")/.." && pwd)"
export NSO_HOME="$NSO_DEMO/nso/current"
export NCS_RUN="$NSO_DEMO/nso/ncs-run"
export NETSIM_DIR="$NSO_DEMO/nso/netsim"
export NED_DIR="$(ls -d "$NSO_DEMO"/nso/neds/cisco-iosxr-cli-* 2>/dev/null | head -1)"
if [ -z "$JAVA_HOME" ] && command -v brew >/dev/null; then
  export JAVA_HOME="$(brew --prefix openjdk@17 2>/dev/null)/libexec/openjdk.jdk/Contents/Home"
fi
source "$NSO_HOME/ncsrc"
echo "NCS_DIR=$NCS_DIR  NED_DIR=$NED_DIR"
```

```bash
# 📁 ~/Projects/NSO_Demo
source scripts/env.sh
ncs --version            # → 6.6.1
```

`env.sh` only *records* paths like `$NCS_RUN`; the folders are created in 6.4.

### 6.4 Create the simulated routers and the NSO runtime directory

```bash
# 📁 any (paths come from env.sh)
ncs-netsim create-network "$NED_DIR" 2 pe --dir "$NETSIM_DIR"   # → pe0, pe1
ncs-setup --netsim-dir "$NETSIM_DIR" --dest "$NCS_RUN"          # → ncs-run/ with ncs.conf, devices, NED link
```

- `ncs-netsim` builds the fake routers.
- `ncs-setup` builds NSO's workspace and pre-registers `pe0`/`pe1`
  (`ncs-cdb/netsim_devices_init.xml`).

### 6.5 Create the start/stop scripts

`scripts/start-lab.sh`

```bash
#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "$0")/env.sh"
ncs-netsim --dir "$NETSIM_DIR" start
(cd "$NCS_RUN" && ncs)
ncs_cli -C -u admin <<'EOF'
devices fetch-ssh-host-keys
devices sync-from
show devices list
EOF
```

`scripts/stop-lab.sh`

```bash
#!/usr/bin/env bash
source "$(dirname "$0")/env.sh"
ncs --stop || true
ncs-netsim --dir "$NETSIM_DIR" stop || true
```

```bash
# 📁 ~/Projects/NSO_Demo
chmod +x scripts/*.sh          # once per machine, otherwise "permission denied"
./scripts/start-lab.sh
```

Expected: `DEVICE pe0/pe1 OK STARTED`, `sync-result ... result true`, and a
device table with both routers on `cisco-iosxr-cli-7.74`, `unlocked`.

> Do **not** use `set -u` in these scripts — Cisco's `ncsrc` reads unset variables.

### 6.6 Capture the NED's XML (template reference)

Push the instructor's config onto the scratch router `pe1`:

```bash
# 📁 any
ncs-netsim --dir "$NETSIM_DIR" cli-c pe1
```

```text
config
<paste device-sample-config/instructor-sample.cfg>
commit
end
exit
```

Ask NSO how the NED models it:

```bash
ncs_cli -C -u admin
```

```text
devices device pe1 sync-from
show running-config devices device pe1 config | display xml | save /Users/<you>/Projects/NSO_Demo/output/pe1-captured.xml
exit
```

`output/pe1-captured.xml` is the **source of truth** for the template element
names (e.g. `mid-thresh`, where `conform-action` sits, `<per-vrf/>`).

### 6.7 Generate the package skeleton

```bash
# 📁 ~/Projects/NSO_Demo/nso/ncs-run/packages
cd "$NCS_RUN/packages"
ncs-make-package --service-skeleton python-and-template --component-class main.Main l3vpn-service
rm l3vpn-service/templates/l3vpn-service-template.xml
ls -R l3vpn-service
```

### 6.8 Write the package files

All inside `nso/ncs-run/packages/l3vpn-service/`:

| File | Content |
|---|---|
| `src/yang/l3vpn-service.yang` | service inputs (section 4) |
| `python/l3vpn_service/main.py` | derived values + applies the 4 templates |
| `templates/l3vpn-vrf.xml` | VRF, RTs (`<?foreach?>`), maximum prefix, IPv6 under `<?if?>` |
| `templates/l3vpn-qos.xml` | ingress police + egress shape policy-maps |
| `templates/l3vpn-interface.xml` | GigabitEthernet sub-interface |
| `templates/l3vpn-bgp.xml` | BGP VRF with RD, label mode, dampening, redistribute |

Template rules:

- Every template starts with the full wrapper
  `<config-template>` → `<devices>` → `<device><name>{/device-name}</name>` → `<config>`.
- Copy the structure from `output/pe1-captured.xml`, then replace values:
  `{/path}` = a YANG input, `{$VAR}` = a value calculated in Python.

### 6.9 Build and load

```bash
# 📁 ~/Projects/NSO_Demo/nso/ncs-run/packages/l3vpn-service/src
cd "$NCS_RUN/packages/l3vpn-service/src"
make clean all                  # compiles YANG → ../load-dir/l3vpn-service.fxs
```

```bash
ncs_cli -C -u admin
```

```text
packages reload                 # both packages must show: result true
```

Only YANG changes need `make`; template/Python changes need only `packages reload`.

---

## 7. Deploy the service

```bash
ncs_cli -C -u admin
```

```text
config
l3vpn-service MSHA-ML3-1-810095
 device-name pe0
 ipv6-enable true
 bandwidth 1676
 vrf vrf-name MSHA-ML-M
 vrf rd-value 71728651
 vrf maximum-prefix limit 20000
 vrf maximum-prefix threshold 80
 qos in-policy-name in_STANDARD_ETH_1676_By_NSO
 qos out-policy-name out_STANDARD_ETH_1676_By_NSO
 qos mpls-exp 0
 interface interface-type GigabitEthernet
 interface interface-id 0/0/1
 interface subintf-id 5002
 interface description MSHA-ML3-1-810095-kjajj-1676k-MSHA-ML3-1-217121-05122024
 interface svlan 3714
 interface cvlan 1260
 interface ip-address 52.45.120.133
 interface subnet-mask 255.255.255.252
 interface ipv6-address 5936:3532::1/126
 vrf route-target 71728651
 top
show configuration
commit dry-run outformat native     ← compare with the instructor's config
commit                              ← "Commit complete."
end
```

Notes:

- If you type only `l3vpn-service <name>`, the CLI prompts **only for mandatory
  leaves**. Add `route-target`, `description` and `ipv6-address` yourself.
- `route-target` is last because creating a list entry enters its sub-mode; `top` returns.
- At a `Value for ...` prompt, `exit` is treated as a value — press **Ctrl+C** to cancel.

---

## 8. Verify and operate

| Goal | Command (in `ncs_cli`) |
|---|---|
| Show service inputs | `show running-config l3vpn-service` |
| Service in sync with device? | `l3vpn-service MSHA-ML3-1-810095 check-sync` |
| What did the service create? | `l3vpn-service MSHA-ML3-1-810095 get-modifications` |
| Device in sync with NSO? | `devices device pe0 check-sync` |
| Save service as XML | `show running-config l3vpn-service \| display xml \| save <abs-path>.xml` |

Check the router itself:

```bash
ncs-netsim --dir "$NETSIM_DIR" cli-c pe0
```

```text
show running-config vrf MSHA-ML-M
show running-config policy-map
show running-config interface GigabitEthernet 0/0/1.5002     ← note the space
show running-config router bgp
exit
```

FASTMAP demos:

```text
! Modify — NSO sends only the diff (rate 2000000, burst 375000, peak 750000)
config
l3vpn-service MSHA-ML3-1-810095 bandwidth 2000
commit dry-run outformat native
revert                       ! or: commit

! Drift — change pe0 by hand in netsim, then:
l3vpn-service MSHA-ML3-1-810095 check-sync          ! → in-sync false
devices device pe0 sync-from
l3vpn-service MSHA-ML3-1-810095 re-deploy dry-run
l3vpn-service MSHA-ML3-1-810095 re-deploy

! Delete — removes exactly what the service created
config
no l3vpn-service MSHA-ML3-1-810095
commit dry-run outformat native
commit
```

Restore a deleted service from saved XML:

```text
config
load merge /Users/<you>/Projects/NSO_Demo/output/service-MSHA.xml
commit
```

---

## 9. Daily usage

```bash
# Start of a session
cd ~/Projects/NSO_Demo
source scripts/env.sh
ncs-netsim --dir "$NETSIM_DIR" is-alive     # running already?
ncs --status | grep status
./scripts/start-lab.sh                      # only if not running (after reboot / stop-lab)

# End of a session
./scripts/stop-lab.sh
```

- Closing a terminal does **not** stop NSO or netsim; they keep running.
  Just open a new terminal and `source scripts/env.sh`.
- Committed config (NSO and netsim) survives stop/start. Uncommitted CLI changes do not.
- Sleeping the Mac is safe; stopping the lab overnight is cleaner.

---

## 10. Running on another Mac

The NSO install, `ncsrc`, netsim and `ncs-run` contain **absolute paths**, so
they cannot simply be copied. On the new machine:

1. Copy the project folder, but **save the package first**:
   `cp -R nso/ncs-run/packages/l3vpn-service ~/l3vpn-service-backup`
2. Remove machine-specific folders:
   `rm -rf nso/nso661 nso/current nso/neds/* nso/netsim nso/ncs-run`
3. Redo sections **6.2 → 6.5** (install, env, netsim, ncs-setup, `chmod +x`, start).
4. Put the package back and build:
   ```bash
   cp -R ~/l3vpn-service-backup "$NCS_RUN/packages/l3vpn-service"
   cd "$NCS_RUN/packages/l3vpn-service/src" && make clean all
   ncs_cli -C -u admin    # then: packages reload
   ```
5. Deploy as in section 7.

---

## 11. Troubleshooting (issues hit during this project)

| Symptom | Cause | Fix |
|---|---|---|
| `zsh: command not found: ncs` / `ncs_cli` / `ncs-netsim` | Terminal has no NSO environment | `cd ~/Projects/NSO_Demo && source scripts/env.sh` |
| `source env.sh` prints nothing | File not saved in VS Code | Cmd+S, source again — must print `NCS_DIR=...` |
| `ncsrc` points to a non-existent folder | NSO install was moved | Re-install with `--local-install <new path>` |
| `binary operator expected` / `is a directory` from `ncs` | NSO path contains a space | Install under a path without spaces |
| `ZSH_VERSION: unbound variable` | `set -u` in a bash script | Use `set -eo pipefail`; use `${ZSH_VERSION:-}` |
| `permission denied: ./scripts/start-lab.sh` | Script not executable | `chmod +x scripts/*.sh` |
| `tar: could not chdir to '../neds'` | Target folder missing | `mkdir -p ../neds` |
| `rg: command not found` | ripgrep not installed | use `grep -E` |
| `address already in use` on start | Lab is already running (or an old NSO) | `is-alive` / `ncs --status`; stop old one or `kill <PID>` |
| `packages reload` → `Unknown element: 'policy-map'` at line 1 | Template missing the `<config-template>/<devices>/<device>/<config>` wrapper | Add the wrapper |
| `Unknown element: 'threshold'` | NED name differs | Use name from capture: `mid-thresh` |
| `too few '... vrf route-target', 0 configured` | `min-elements 1` | `l3vpn-service <name> vrf route-target 71728651` |
| `interface/ipv6-address is required ...` | `must` rule | Add `interface ipv6-address ...` |
| `syntax error: element does not exist` on `show ... GigabitEthernet0/0/1.5002` | netsim show uses NED path | `show running-config interface GigabitEthernet 0/0/1.5002` |
| Pylance: `Import "ncs" could not be resolved` | VS Code doesn't know NSO's Python path | Harmless; optionally add `.vscode/settings.json` (below) |
| Python errors after reload | Bug in `main.py` | `tail -50 "$NCS_RUN/logs/ncs-python-vm-l3vpn-service.log"` |

Optional `.vscode/settings.json`:

```json
{
  "python.analysis.extraPaths": ["${workspaceFolder}/nso/current/src/ncs/pyapi"]
}
```

---

## 12. Security notes

- **No credentials are stored** in any script or file. `ncs_cli -u admin`
  logs in over NSO's local IPC and needs no password.
- netsim's `admin/admin` is a **lab-only default** created by `ncs-setup`.
  For real devices create an NSO authgroup and enter the password
  interactively (stored encrypted in CDB) — never put passwords in files or git.
- Installers were verified with Cisco's certificate chain (`crcam2.cer` →
  `innerspace.cer` → `tailf.cer`: RSA 4096, SHA-512, valid until 2037).
  Do not use `--skip-verification`.

---

## 13. Next steps

- Add `TenGigE` / `Bundle-Ether` to the `interface-type` enum and an
  `<?elif?>` block in `l3vpn-interface.xml`.
- Clarify with the instructor whether burst/peak-burst should be manual inputs
  (supported today via the optional `qos burst` / `qos peak-burst` leaves).
- Move the package source out of `ncs-run` (e.g. `NSO_Demo/packages/`) and
  symlink it into `ncs-run/packages/`, so `ncs-run` can be rebuilt safely.
- Put the project under git (ignore `nso/nso661`, `nso/netsim`, `nso/ncs-run`
  except the package, and `load-dir/`).
