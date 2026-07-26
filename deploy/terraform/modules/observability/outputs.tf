# =============================================================================
# Módulo: Observability — Outputs
# =============================================================================

output "log_group_name" {
  description = "Nome do CloudWatch Log Group para ECS."
  value       = aws_cloudwatch_log_group.ecs_api.name
}

output "log_group_arn" {
  description = "ARN do CloudWatch Log Group para ECS."
  value       = aws_cloudwatch_log_group.ecs_api.arn
}

output "dashboard_url" {
  description = "URL do CloudWatch Dashboard."
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_caller_identity.current.region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "insights_queries" {
  description = "Mapa de CloudWatch Insights queries salvas."
  value = {
    errors_by_hour   = aws_cloudwatch_query_definition.errors_by_hour.name
    request_latency  = aws_cloudwatch_query_definition.request_latency.name
    errors_by_endpoint = aws_cloudwatch_query_definition.errors_by_endpoint.name
    model_performance = aws_cloudwatch_query_definition.model_performance.name
    model_sync       = aws_cloudwatch_query_definition.model_sync.name
  }
}

output "alarms" {
  description = "Mapa de CloudWatch Alarms criados."
  value = {
    alb_target_5xx_high    = aws_cloudwatch_metric_alarm.alb_target_5xx_high.alarm_name
    alb_target_latency_high = aws_cloudwatch_metric_alarm.alb_target_latency_high.alarm_name
    alb_target_unhealthy   = aws_cloudwatch_metric_alarm.alb_target_unhealthy.alarm_name
    ecs_cpu_high           = aws_cloudwatch_metric_alarm.ecs_cpu_high.alarm_name
    ecs_memory_high        = aws_cloudwatch_metric_alarm.ecs_memory_high.alarm_name
  }
}
