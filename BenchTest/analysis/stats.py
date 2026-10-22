"""Repeatability statistics: coefficient of variation with a bootstrap CI, and intraclass correlation with F-based CI.

ICC follows Shrout and Fleiss (1979) and McGraw and Wong (1996), two-way model, single measurement:
  rows (targets) = road sections, columns (raters) = passes (pass 1, 2, ... over every section).
  ICC(2,1)  absolute agreement, random passes:   (MSR - MSE) / (MSR + (k-1) MSE + k (MSC - MSE) / n)
  ICC(3,1)  consistency, fixed passes:           (MSR - MSE) / (MSR + (k-1) MSE)
CIs: ICC(3,1) from the exact F distribution; ICC(2,1) from the McGraw and Wong approximation (Satterthwaite df).
Checked in tests against the Shrout and Fleiss example (6 targets, 4 judges): ICC(2,1) = 0.29, ICC(3,1) = 0.71.
"""
import numpy as np
from scipy import stats as st


def cv(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 2 or x.mean() == 0:
        return float("nan")
    return float(np.std(x, ddof=1) / abs(np.mean(x)))


def bootstrap_ci(x, fn, n_boot=2000, alpha=0.05, seed=1):
    """Percentile bootstrap CI of fn over resamples of x (with replacement)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    vals = np.array([fn(x[i]) for i in idx])
    vals = vals[np.isfinite(vals)]
    if not len(vals):
        return float("nan"), float("nan")
    return float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2))


def icc(Y, alpha=0.05):
    """ICC(2,1) and ICC(3,1) of an n x k matrix (rows: sections, columns: passes). Rows with NaN are dropped."""
    Y = np.asarray(Y, float)
    Y = Y[np.all(np.isfinite(Y), axis=1)]
    n, k = Y.shape if Y.ndim == 2 else (0, 0)
    out = {"n_sections": int(n), "k_passes": int(k)}
    if n < 2 or k < 2:
        out.update({"icc2_1": np.nan, "icc2_1_ci": (np.nan, np.nan), "icc3_1": np.nan, "icc3_1_ci": (np.nan, np.nan)})
        return out
    gm = Y.mean()
    ssr = k * np.sum((Y.mean(axis=1) - gm) ** 2)
    ssc = n * np.sum((Y.mean(axis=0) - gm) ** 2)
    sst = np.sum((Y - gm) ** 2)
    sse = sst - ssr - ssc
    dfr, dfc, dfe = n - 1, k - 1, (n - 1) * (k - 1)
    msr, msc, mse = ssr / dfr, ssc / dfc, max(sse, 0.0) / dfe
    out.update({"MSR": msr, "MSC": msc, "MSE": mse})
    if mse <= 1e-15 * max(msr, 1e-300):
        # passes identical within each section: perfect agreement (if sections differ at all)
        one = 1.0 if msr > 0 else np.nan
        same = msc <= 1e-15 * max(msr, 1e-300)
        out.update({"icc2_1": one if same else float(msr / (msr + k * msc / n)),
                    "icc2_1_ci": (one, one) if same else (np.nan, np.nan),
                    "icc3_1": one, "icc3_1_ci": (one, one), "F": np.inf})
        return out
    icc3 = (msr - mse) / (msr + (k - 1) * mse)
    icc2 = (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)
    F = msr / mse
    q = 1 - alpha / 2
    fl = F / st.f.ppf(q, dfr, dfe)
    fu = F * st.f.ppf(q, dfe, dfr)
    ci3 = ((fl - 1) / (fl + k - 1), (fu - 1) / (fu + k - 1))
    # McGraw and Wong (1996), case 2A
    a = k * icc2 / (n * (1 - icc2))
    b = 1 + k * icc2 * (n - 1) / (n * (1 - icc2))
    v = (a * msc + b * mse) ** 2 / ((a * msc) ** 2 / dfc + (b * mse) ** 2 / dfe)
    fs_ = st.f.ppf(q, dfr, v)
    fs2 = st.f.ppf(q, v, dfr)
    lo = n * (msr - fs_ * mse) / (fs_ * (k * msc + (k * n - k - n) * mse) + n * msr)
    hi = n * (fs2 * msr - mse) / (k * msc + (k * n - k - n) * mse + n * fs2 * msr)
    out.update({"icc2_1": float(icc2), "icc2_1_ci": (float(lo), float(hi)), "icc3_1": float(icc3),
                "icc3_1_ci": (float(ci3[0]), float(ci3[1])), "F": float(F), "df": (dfr, dfe)})
    return out


def repeatability(rows, metrics=("a_w", "vdv", "sigma", "sigma_1s_median", "index_sigma2_per_v"), n_boot=2000,
                  seed=1):
    """Repeatability across passes.

    rows: per-pass dicts with "section", "pass_no" (or order of appearance) and metric values.
    Returns {"per_section": [ {section, metric, n, mean, sd, cv, cv_ci_lo, cv_ci_hi} ], "icc": {metric: icc dict}}.
    For the ICC the pass index is the column; only passes present in every section are used.
    """
    secs = {}
    for r in rows:
        secs.setdefault(r.get("section") or "all", []).append(r)
    per = []
    for s, rs in secs.items():
        for m in metrics:
            x = np.array([r.get(m, np.nan) for r in rs], float)
            x = x[np.isfinite(x)]
            lo, hi = bootstrap_ci(x, cv, n_boot, seed=seed)
            per.append({"section": s, "metric": m, "n": int(len(x)),
                        "mean": float(np.mean(x)) if len(x) else np.nan,
                        "sd": float(np.std(x, ddof=1)) if len(x) > 1 else np.nan,
                        "cv": cv(x), "cv_ci_lo": lo, "cv_ci_hi": hi})
    icc_out = {}
    if len(secs) >= 2:
        for m in metrics:
            cols = None
            table = {}
            for s, rs in secs.items():
                d = {}
                for j, r in enumerate(rs):
                    p = r.get("pass_no") if r.get("pass_no") is not None else j + 1
                    d[p] = r.get(m, np.nan)
                table[s] = d
                cols = set(d) if cols is None else cols & set(d)
            cols = sorted(cols or [])
            Y = np.array([[table[s][p] for p in cols] for s in table], float) if cols else np.zeros((0, 0))
            icc_out[m] = icc(Y)
            icc_out[m]["passes_used"] = cols
    return {"per_section": per, "icc": icc_out}
