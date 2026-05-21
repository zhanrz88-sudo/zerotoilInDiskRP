# DiskRP Tools

On-call toolbox for DiskRP operations. Available online at [GitHub Pages](https://zhanrz88-sudo.github.io/zerotoilInDiskRP/) or locally.

## Tools

### 🔑 Approve Feature (`approve-feature.html`)

Generate SAW links for `ApproveFeatureRegistration` via Geneva Actions.

**Usage:** Enter a subscription ID → get a Geneva portal link + Python snippet with all params filled.

- **Online:** https://zhanrz88-sudo.github.io/zerotoilInDiskRP/tools/approve-feature.html
- **Local:** Open `tools/approve-feature.html` in any browser (no server needed)
- Supports custom feature names and remembers last 10 approvals

> ⚠️ Requires SAW with JIT `DiskRP-PlatformServiceOperator` — backend worker cannot approve features.

---

### 🔗 Break ISF (`break-isf.html`)

`RemoveIncrementalSnapshotFamilyOnDisk` — enter a disk name, auto-lookup subscription/region/RG via Kusto, get SAW links.

**Two modes:**

#### With local server (recommended — auto-fills Geneva link)
```powershell
cd C:\git\zerotoilfordiskRP
python tools\break_isf_server.py
```
- Opens browser at `http://localhost:8091`
- Enter disk name → Kusto lookup → Geneva portal link + Python snippet
- Keep server running while using the page. Ctrl+C to stop.

#### Without local server (online / GitHub Pages)
- **Online:** https://zhanrz88-sudo.github.io/zerotoilInDiskRP/tools/break-isf.html
- Enter disk name → generates a self-contained Python snippet with Kusto lookup built in
- Copy snippet → paste into SAW JupyterLite → it does lookup + Break ISF

> ⚠️ Mutating operation — requires SAW with JIT `DiskRP-CustomerServiceOperator`.

---

### CLI alternative

```powershell
python tools\break_isf.py <diskName>
python tools\break_isf.py <diskName> --skip-validation --clear-billing
```

Queries Kusto locally via `az rest`, prints Geneva link + Python snippet.
