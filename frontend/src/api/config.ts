import request from "./index";

export interface RiskRule {
  id: number;
  rule_name: string;
  trigger_conditions: Record<string, unknown>;
  risk_level: string;
  risk_tag: string | null;
  alert_message: string | null;
  is_active: boolean;
}

export const getConfig = () =>
  request.get<{ data: Record<string, unknown> }>("/config").then((r) => r.data.data);

export const updateThresholds = (body: Record<string, unknown>) =>
  request.put<{ data: Record<string, unknown> }>("/config/thresholds", body).then((r) => r.data.data);

export const getRiskRules = () =>
  request.get<{ data: { items: RiskRule[] } }>("/config/risk-rules").then((r) => r.data.data);

export const createRiskRule = (body: Partial<RiskRule>) =>
  request.post<{ data: RiskRule }>("/config/risk-rules", body).then((r) => r.data.data);

export const updateRiskRule = (id: number, body: Partial<RiskRule>) =>
  request.put<{ data: RiskRule }>(`/config/risk-rules/${id}`, body).then((r) => r.data.data);

export const deleteRiskRule = (id: number) =>
  request.delete(`/config/risk-rules/${id}`).then((r) => r.data);