import request from "./index";

export interface DailyReportData {
  id: number;
  report_date: string;
  recommendations: string | null;
  trend_analysis: string | null;
  risk_alerts: string | null;
  action_suggestions: string | null;
  model_used: string;
  generation_time_ms: number | null;
}

export const getTodayReport = () =>
  request.get<{ data: DailyReportData | null }>("/reports/daily").then((r) => r.data.data);

export const getReportByDate = (date: string) =>
  request.get<{ data: DailyReportData }>(`/reports/daily/${date}`).then((r) => r.data.data);

export const triggerGenerate = (date?: string, force: boolean = false) =>
  request.post<{ data: { task_id: string } }>("/reports/generate", null, { params: { report_date: date, force } }).then((r) => r.data.data);