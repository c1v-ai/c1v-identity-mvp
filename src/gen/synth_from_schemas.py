# src/gen/synth_from_schemas.py
# CLI to generate synthetic leads/sales/financial and labeled pairs.
# Requirements: pandas, faker, pyarrow

from __future__ import annotations
import argparse, json, os, random, string, hashlib, time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from faker import Faker


# ----------------------------- utils -----------------------------

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def maybe_hash(v: str | int | float | None, mode: str, salt: str) -> str | int | float | None:
    if v is None or mode == "plain":
        return v
    return sha256_hex(f"{salt}:{v}")

@dataclass
class SynthConfig:
    n_leads: int
    n_sales: int
    n_financial: int
    dup_rate: float
    overlap: float
    seed: int
    pii: str  # "plain" | "hashed"
    salt: str
    locale: str  # "US" | "CA" | "US+CA"


# ---------------------- base population build --------------------

def build_base_persons(fake: Faker, m: int, rng: random.Random, locale: str) -> pd.DataFrame:
    rows = []
    for i in range(m):
        first = fake.first_name()
        last = fake.last_name()
        email_local = (first + "." + last).lower()
        domain = rng.choice(["gmail.com", "yahoo.com", "outlook.com", "example.com"]) 
        email = f"{email_local}@{domain}"
        phone = fake.phone_number()
        addr = fake.street_address()
        city = fake.city()
        state = getattr(fake, "state_abbr", lambda: "CA")()
        zipc = fake.postcode()
        country = "US" if locale.startswith("US") else "CA"
        rows.append({
            "entity_id": i,
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": phone,
            "address": addr,
            "city": city,
            "state": state,
            "zip": zipc,
            "country": country,
        })
    return pd.DataFrame(rows)


# -------------------- noise / duplicate variants -----------------

def nickname(first: str) -> str:
    m = {
        "alex": ["alex", "alexander", "al"],
        "michael": ["michael", "mike"],
        "elizabeth": ["elizabeth", "liz", "beth"],
        "katherine": ["katherine", "kate", "kat"],
    }
    key = first.lower()
    return random.choice(m.get(key, [first]))


def rand_case(s: str, rng: random.Random) -> str:
    return "".join(ch.upper() if rng.random() < 0.5 else ch.lower() for ch in s)


def plus_alias(email: str, rng: random.Random) -> str:
    try:
        local, domain = email.split("@", 1)
        tag = "".join(rng.choice(string.ascii_lowercase + string.digits) for _ in range(4))
        return f"{local}+{tag}@{domain}"
    except Exception:
        return email


def typo1(s: str, rng: random.Random) -> str:
    if not s:
        return s
    i = rng.randrange(0, len(s))
    c = rng.choice(string.ascii_lowercase)
    return s[:i] + c + s[i+1:]


def make_variant(row: Dict, rng: random.Random) -> Dict:
    r = dict(row)
    # Apply a few light variants
    if rng.random() < 0.5:
        r["first_name"] = nickname(r.get("first_name", ""))
    if rng.random() < 0.5 and r.get("email"):
        r["email"] = plus_alias(r["email"], rng)
    if rng.random() < 0.3 and r.get("last_name"):
        r["last_name"] = rand_case(r["last_name"], rng)
    if rng.random() < 0.2 and r.get("address"):
        r["address"] = typo1(r["address"], rng)
    return r


# ----------------------- source generation -----------------------

def pick_overlap_ids(base_ids: List[int], n: int, overlap_ratio: float, rng: random.Random) -> Tuple[List[int], List[int]]:
    k = int(min(n, len(base_ids)) * overlap_ratio)
    overlap = rng.sample(base_ids, k) if k > 0 else []
    new_needed = n - len(overlap)
    new_ids = list(range(max(base_ids) + 1, max(base_ids) + 1 + new_needed))
    return overlap, new_ids


def assemble_source(name: str, base: pd.DataFrame, n: int, overlap_ratio: float, dup_rate: float, rng: random.Random) -> pd.DataFrame:
    base_ids = base["entity_id"].tolist()
    overlap_ids, new_ids = pick_overlap_ids(base_ids, n, overlap_ratio, rng)
    take = base[base.entity_id.isin(overlap_ids)].copy()

    # create new rows for remaining
    if new_ids:
        f = Faker()
        extra = build_base_persons(f, len(new_ids), rng, locale="US")
        extra["entity_id"] = new_ids
        base = pd.concat([base, extra], ignore_index=True)
        take = pd.concat([take, extra], ignore_index=True)

    take = take.sample(frac=1.0, random_state=rng.randrange(1, 10**9)).head(n).reset_index(drop=True)

    # per-source column naming differences
    if name == "leads":
        take["company"] = take["last_name"] + " LLC"
        take["source"] = rng.choice(["web", "event", "partner"])
    elif name == "sales":
        take["account"] = take["last_name"] + " Holdings"
        take["order_id"] = [f"SO-{100000 + i}" for i in range(len(take))]
        take["order_value"] = [round(random.uniform(100, 5000), 2) for _ in range(len(take))]
        take["order_date"] = pd.Timestamp("today").normalize()
    elif name == "financial":
        take["account"] = take["last_name"] + " Holdings"
        take["invoice_id"] = [f"INV-{100000 + i}" for i in range(len(take))]
        take["amount"] = [round(random.uniform(50, 6000), 2) for _ in range(len(take))]
        take["invoice_date"] = pd.Timestamp("today").normalize()

    # inject duplicates
    dups = int(max(0, dup_rate) * len(take))
    variants = []
    for _ in range(dups):
        src_row = take.sample(1, random_state=rng.randrange(1, 10**9)).iloc[0].to_dict()
        variants.append(make_variant(src_row, rng))
    if variants:
        take = pd.concat([take, pd.DataFrame(variants)], ignore_index=True)
        take = take.head(n)  # cap to n

    # add an id per source row
    take.insert(0, "id", [f"{name[:1]}-{i}" for i in range(1, len(take) + 1)])
    return take


# --------------------------- pairs -------------------------------

def build_pairs(leads: pd.DataFrame, sales: pd.DataFrame, financial: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    frames = {"leads": leads, "sales": sales, "financial": financial}

    # map from entity_id to rows per source
    by_ent: Dict[int, Dict[str, List[Dict]]] = {}
    for src, df in frames.items():
        for rec in df.to_dict(orient="records"):
            ent = rec.get("entity_id")
            by_ent.setdefault(ent, {}).setdefault(src, []).append(rec)

    # positives: pair across sources for same entity_id
    pos = []
    sources = list(frames.keys())
    for ent, buckets in by_ent.items():
        present = [s for s in sources if s in buckets]
        if len(present) < 2:
            continue
        # pair the first occurrence across each pair of sources
        if "leads" in present and "sales" in present:
            pos.append(("leads", buckets["leads"][0], "sales", buckets["sales"][0], 1))
        if "leads" in present and "financial" in present:
            pos.append(("leads", buckets["leads"][0], "financial", buckets["financial"][0], 1))
        if "sales" in present and "financial" in present:
            pos.append(("sales", buckets["sales"][0], "financial", buckets["financial"][0], 1))

    # hard negatives: same email local-part but different domain; or same zip but different email
    neg = []
    def local_part(e: str) -> str:
        return (e or "").split("@")[0].lower()

    # index by local part
    idx_local = {}
    for src, df in frames.items():
        for rec in df.to_dict(orient="records"):
            lp = local_part(rec.get("email", ""))
            idx_local.setdefault(lp, []).append((src, rec))

    for lp, items in idx_local.items():
        # cross pair different domains
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (s1, r1), (s2, r2) = items[i], items[j]
                d1 = (r1.get("email", "").split("@") + [""])[-1]
                d2 = (r2.get("email", "").split("@") + [""])[-1]
                if d1 and d2 and d1 != d2 and r1.get("entity_id") != r2.get("entity_id"):
                    neg.append((s1, r1, s2, r2, 0))

   
        # fallback (bounded): sample zip-based negatives up to 3x positives, but stop after N tries
        target = 2 * max(1, len(pos))   # lower than 3x to speed up
        tries = 0
        max_tries = 5000
        while len(neg) < target and tries < max_tries:
            s1, s2 = random.sample(list(frames.keys()), 2)
            r1 = frames[s1].sample(1).iloc[0].to_dict()
            r2 = frames[s2].sample(1).iloc[0].to_dict()
            if r1.get("zip") == r2.get("zip") and r1.get("email") != r2.get("email"):
                neg.append((s1, r1, s2, r2, 0))
            tries += 1
        # proceed even if we didn't fully hit target
        


# --------------------------- driver ------------------------------

def run(cfg: SynthConfig, schema_path: str, outdir: str, pairs_out: str) -> dict:
    rng = random.Random(cfg.seed)
    locale = "en_US" if cfg.locale.startswith("US") else "en_CA"
    fake = Faker(locale)
    Faker.seed(cfg.seed)

    Path(outdir).mkdir(parents=True, exist_ok=True)
    Path(pairs_out).mkdir(parents=True, exist_ok=True)
    Path("reports").mkdir(parents=True, exist_ok=True)

    # read schema if present (not strictly required in Stage 1)
    if schema_path and Path(schema_path).exists():
        try:
            _ = json.loads(Path(schema_path).read_text())
        except Exception:
            pass

    base_n = int(max(cfg.n_leads, cfg.n_sales, cfg.n_financial) * max(0.1, min(1.0, cfg.overlap)))
    base = build_base_persons(fake, base_n, rng, cfg.locale)

    leads = assemble_source("leads", base.copy(), cfg.n_leads, cfg.overlap, cfg.dup_rate, rng)
    sales = assemble_source("sales", base.copy(), cfg.n_sales, cfg.overlap, cfg.dup_rate, rng)
    financial = assemble_source("financial", base.copy(), cfg.n_financial, cfg.overlap, cfg.dup_rate, rng)

    # optional hashing
    if cfg.pii == "hashed":
        salt = cfg.salt or "c1v_salt"
        for df in (leads, sales, financial):
            for col in ["email", "phone", "first_name", "last_name", "address"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).apply(lambda v: maybe_hash(v, cfg.pii, salt))

    # write CSVs
    leads.to_csv(Path(outdir) / "leads.csv", index=False)
    sales.to_csv(Path(outdir) / "sales.csv", index=False)
    financial.to_csv(Path(outdir) / "financial.csv", index=False)

    # build pairs
    pairs = build_pairs(leads, sales, financial, rng)

    # train/valid/test split 70/15/15
    def split_df(df: pd.DataFrame, rng: random.Random) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        df = df.sample(frac=1.0, random_state=rng.randrange(1, 10**9)).reset_index(drop=True)
        n = len(df)
        n_train = int(0.7 * n)
        n_valid = int(0.15 * n)
        return df.iloc[:n_train], df.iloc[n_train:n_train+n_valid], df.iloc[n_train+n_valid:]

    train, valid, test = split_df(pairs, rng)

    # write parquet (requires pyarrow)
    train.to_parquet(Path(pairs_out) / "train.parquet")
    valid.to_parquet(Path(pairs_out) / "valid.parquet")
    test.to_parquet(Path(pairs_out) / "test.parquet")

    summary = {
        "seed": cfg.seed,
        "sizes": {"leads": len(leads), "sales": len(sales), "financial": len(financial)},
        "pairs": {"total": len(pairs), "train": len(train), "valid": len(valid), "test": len(test)},
        "dup_rate": cfg.dup_rate,
        "overlap": cfg.overlap,
        "pii": cfg.pii,
        "generated_at": int(time.time()),
    }
    Path("reports/synth_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main():
    ap = argparse.ArgumentParser(description="C1V synthetic generator")
    ap.add_argument("--schema", default="automotive_schemas.json")
    ap.add_argument("--outdir", default="data/synth")
    ap.add_argument("--pairs-out", default="data/pairs")
    ap.add_argument("--n-leads", type=int, default=1000)
    ap.add_argument("--n-sales", type=int, default=1000)
    ap.add_argument("--n-financial", type=int, default=1000)
    ap.add_argument("--dup-rate", type=float, default=0.10)
    ap.add_argument("--overlap", type=float, default=0.40)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--pii", choices=["plain", "hashed"], default="plain")
    ap.add_argument("--salt", default="c1v_salt")
    ap.add_argument("--locale", choices=["US", "CA", "US+CA"], default="US+CA")
    args = ap.parse_args()

    cfg = SynthConfig(
        n_leads=args.n_leads,
        n_sales=args.n_sales,
        n_financial=args.n_financial,
        dup_rate=args.dup_rate,
        overlap=args.overlap,
        seed=args.seed,
        pii=args.pii,
        salt=args.salt,
        locale=args.locale,
    )
    summary = run(cfg, args.schema, args.outdir, args.pairs_out)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

