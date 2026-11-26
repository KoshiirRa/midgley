/**
 * Edge Asymmetric Error-Correction Model (ECM) Evaluator (workers/asymmetric_ecm_evaluator.ts)
 *
 * Zero-dependency TypeScript econometric evaluator matching Python `src/asymmetric_ecm.py`
 * (`AsymmetricECM.predict_step_ahead`) for real-time edge price & shock nowcasting (Issue #642).
 *
 * All outputs are strictly labeled `PROSPECTIVE_EDGE_NOWCAST` and never mixed with
 * historical observed ground truth.
 */

export interface EcmCoefficients {
  hub_key: string;
  model_version: string;
  beta: number;
  equilibrium_margin_c: number;
  alpha_pos: number;
  alpha_neg: number;
  gamma_pos_coefs: number[];
  gamma_neg_coefs: number[];
  delta_coefs: number[];
  intercept_dynamic: number;
  n_lags_wholesale: number;
  n_lags_retail: number;
  last_retail_price: number;
  last_wholesale_price: number;
  last_d_wholesale_lags: number[];
  last_d_retail_lags: number[];
  max_step_delta?: number;
  min_step_delta?: number;
  exported_at?: string;
}

export interface EdgeNowcastInput {
  current_retail?: number;
  current_wholesale?: number;
  expected_wholesale_deltas?: number[];
  horizon_days?: number;
  tax_delta_loc?: number;
  apply_plausibility_bounds?: boolean;
}

export interface EdgeNowcastResult {
  status: "success";
  provenance: "PROSPECTIVE_EDGE_NOWCAST";
  is_simulation: boolean;
  hub_key: string;
  model_version: string;
  horizon_days: number;
  current_retail: number;
  current_wholesale: number;
  disequilibrium_z0: number;
  tax_delta_loc: number;
  trajectory: number[];
  terminal_price: number;
  expected_delta: number;
  invariants_valid: boolean;
}

export const ECM_COEFFICIENTS_D1_SCHEMA = `
CREATE TABLE IF NOT EXISTS edge_ecm_coefficients (
  hub_key TEXT PRIMARY KEY,
  model_version TEXT NOT NULL,
  coefficients_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
`;

export const DEFAULT_EDGE_ECM_COEFFICIENTS: Record<string, EcmCoefficients> = {
  national: {
    hub_key: "national",
    model_version: "ecm-edge-default-v1",
    beta: 1.0,
    equilibrium_margin_c: 0.85,
    alpha_pos: -0.05,
    alpha_neg: -0.15,
    gamma_pos_coefs: [0.35, 0.25, 0.15, 0.08],
    gamma_neg_coefs: [0.18, 0.14, 0.10, 0.06],
    delta_coefs: [0.10, 0.04],
    intercept_dynamic: 0.0,
    n_lags_wholesale: 3,
    n_lags_retail: 2,
    last_retail_price: 3.25,
    last_wholesale_price: 2.40,
    last_d_wholesale_lags: [0.0, 0.0, 0.0],
    last_d_retail_lags: [0.0, 0.0],
    max_step_delta: 0.35,
    min_step_delta: -0.25,
  },
};

function round4(val: number): number {
  return Math.round(val * 10000) / 10000;
}

export class AsymmetricECMEvaluator {
  private readonly coef: EcmCoefficients;

  constructor(coefficients: EcmCoefficients) {
    this.coef = coefficients;
  }

  /**
   * Checks core economic invariants: error correction speeds negative (mean-reverting)
   * and long-run wholesale pass-through beta within plausible bounds.
   */
  public validateInvariants(): boolean {
    return (
      this.coef.alpha_pos <= 0.0 &&
      this.coef.alpha_neg <= 0.0 &&
      this.coef.beta >= 0.5 &&
      this.coef.beta <= 1.5
    );
  }

  /**
   * Evaluates h-step ahead retail price trajectory matching Python
   * `AsymmetricECM.predict_step_ahead()`.
   */
  public evaluate(input: EdgeNowcastInput = {}): EdgeNowcastResult {
    const totalSteps = Math.max(1, Math.min(14, Math.floor(input.horizon_days ?? 5)));
    const taxDeltaLoc = Number.isFinite(input.tax_delta_loc) ? Number(input.tax_delta_loc) : 0.0;
    const applyBounds = input.apply_plausibility_bounds ?? false;
    const maxStep = this.coef.max_step_delta ?? 0.35;
    const minStep = this.coef.min_step_delta ?? -0.25;

    let retPrice =
      input.current_retail !== undefined && Number.isFinite(input.current_retail)
        ? Number(input.current_retail)
        : this.coef.last_retail_price;
    let whlPrice =
      input.current_wholesale !== undefined && Number.isFinite(input.current_wholesale)
        ? Number(input.current_wholesale)
        : this.coef.last_wholesale_price;

    const baseRetail = retPrice;
    const baseWholesale = whlPrice;
    const z0 = retPrice - (this.coef.beta * whlPrice + this.coef.equilibrium_margin_c);

    // Warm start historical difference buffers (exact parity with Python)
    let dRetHist: number[] =
      this.coef.last_d_retail_lags.length === this.coef.n_lags_retail
        ? [...this.coef.last_d_retail_lags]
        : new Array(this.coef.n_lags_retail).fill(0.0);

    let dWhlPosHist: number[] = [
      0.0,
      ...this.coef.last_d_wholesale_lags.map((x) => Math.max(0.0, x)),
    ];
    let dWhlNegHist: number[] = [
      0.0,
      ...this.coef.last_d_wholesale_lags.map((x) => Math.min(0.0, x)),
    ];

    let whlDeltas: number[];
    if (!input.expected_wholesale_deltas || input.expected_wholesale_deltas.length === 0) {
      whlDeltas = new Array(totalSteps).fill(0.0);
    } else if (input.expected_wholesale_deltas.length === 1 && totalSteps > 1) {
      const perStep = input.expected_wholesale_deltas[0] / totalSteps;
      whlDeltas = new Array(totalSteps).fill(perStep);
    } else {
      whlDeltas = [...input.expected_wholesale_deltas];
      while (whlDeltas.length < totalSteps) {
        whlDeltas.push(0.0);
      }
    }

    const trajectory: number[] = [];

    for (let step = 0; step < totalSteps; step++) {
      const dW = whlDeltas[step];
      const dWPos = Math.max(0.0, dW);
      const dWNeg = Math.min(0.0, dW);

      dWhlPosHist[0] = dWPos;
      dWhlNegHist[0] = dWNeg;

      const z = retPrice - (this.coef.beta * whlPrice + this.coef.equilibrium_margin_c);
      const zPos = Math.max(0.0, z);
      const zNeg = Math.min(0.0, z);

      let srPos = 0.0;
      for (let i = 0; i < Math.min(this.coef.gamma_pos_coefs.length, dWhlPosHist.length); i++) {
        srPos += this.coef.gamma_pos_coefs[i] * dWhlPosHist[i];
      }
      let srNeg = 0.0;
      for (let i = 0; i < Math.min(this.coef.gamma_neg_coefs.length, dWhlNegHist.length); i++) {
        srNeg += this.coef.gamma_neg_coefs[i] * dWhlNegHist[i];
      }
      let arRet = 0.0;
      for (let j = 0; j < Math.min(this.coef.delta_coefs.length, dRetHist.length); j++) {
        arRet += this.coef.delta_coefs[j] * dRetHist[j];
      }

      let dRetailPred =
        this.coef.intercept_dynamic +
        this.coef.alpha_pos * zPos +
        this.coef.alpha_neg * zNeg +
        srPos +
        srNeg +
        arRet;

      if (applyBounds) {
        dRetailPred = Math.max(minStep, Math.min(maxStep, dRetailPred));
      }

      whlPrice += dW;
      retPrice += dRetailPred;
      trajectory.push(round4(retPrice + taxDeltaLoc));

      if (dRetHist.length > 0) {
        dRetHist = [dRetailPred, ...dRetHist.slice(0, -1)];
      }
      if (dWhlPosHist.length > 0) {
        dWhlPosHist = [dWPos, ...dWhlPosHist.slice(0, -1)];
      }
      if (dWhlNegHist.length > 0) {
        dWhlNegHist = [dWNeg, ...dWhlNegHist.slice(0, -1)];
      }
    }

    const terminalPrice = trajectory[trajectory.length - 1];
    return {
      status: "success",
      provenance: "PROSPECTIVE_EDGE_NOWCAST",
      is_simulation: false,
      hub_key: this.coef.hub_key,
      model_version: this.coef.model_version,
      horizon_days: totalSteps,
      current_retail: round4(baseRetail),
      current_wholesale: round4(baseWholesale),
      disequilibrium_z0: round4(z0),
      tax_delta_loc: round4(taxDeltaLoc),
      trajectory,
      terminal_price: terminalPrice,
      expected_delta: round4(terminalPrice - baseRetail),
      invariants_valid: this.validateInvariants(),
    };
  }
}

export async function loadEcmCoefficientsFromD1(
  db: any,
  hubKey: string
): Promise<EcmCoefficients> {
  const normalized = (hubKey || "national").trim().toLowerCase();
  if (db) {
    try {
      const row = await db
        .prepare(
          "SELECT coefficients_json FROM edge_ecm_coefficients WHERE hub_key = ? LIMIT 1"
        )
        .bind(normalized)
        .first();
      if (row && typeof row.coefficients_json === "string") {
        return JSON.parse(row.coefficients_json) as EcmCoefficients;
      }
    } catch (err) {
      console.warn("[Edge ECM D1 Notice]", err);
    }
  }
  return DEFAULT_EDGE_ECM_COEFFICIENTS[normalized] ?? DEFAULT_EDGE_ECM_COEFFICIENTS.national;
}
