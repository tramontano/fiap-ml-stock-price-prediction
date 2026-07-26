# =============================================================================
# Módulo: Observability — CloudWatch Logs, Insights, Alarms
#
# Este módulo centraliza a observabilidade da aplicação:
#   • CloudWatch Log Groups para ECS
#   • CloudWatch Insights para análise de logs estruturados
#   • CloudWatch Alarms para monitoramento de performance
#   • Dashboards para visualização de métricas
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(var.tags, {
    Module      = "observability"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# CloudWatch Log Group — Centraliza logs do ECS
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "ecs_api" {
  name              = "/ecs/${local.name_prefix}-api"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-logs"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# CloudWatch Alarms — Monitoramento de Performance
# ─────────────────────────────────────────────────────────────────────────────

# Alarme: Taxa de erro alta (> 5% de respostas 5xx)
resource "aws_cloudwatch_metric_alarm" "alb_target_5xx_high" {
  alarm_name          = "${local.name_prefix}-alb-target-5xx-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = var.alarm_5xx_threshold
  alarm_description   = "Alerta quando a taxa de erros 5xx ultrapassa o limite"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : []
}

# Alarme: Latência alta (> 1000ms)
resource "aws_cloudwatch_metric_alarm" "alb_target_latency_high" {
  alarm_name          = "${local.name_prefix}-alb-target-latency-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = var.alarm_latency_threshold / 1000  # Convertido para segundos
  alarm_description   = "Alerta quando a latência média ultrapassa o limite"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : []
}

# Alarme: Targets unhealthy (health check falhando)
resource "aws_cloudwatch_metric_alarm" "alb_target_unhealthy" {
  alarm_name          = "${local.name_prefix}-alb-target-unhealthy"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "Alerta quando há targets unhealthy"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : []
}

# Alarme: ECS CPU alta (> 80%)
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "${local.name_prefix}-ecs-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_ecs_cpu_threshold
  alarm_description   = "Alerta quando CPU do ECS ultrapassa o limite"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : []
}

# Alarme: ECS Memory alta (> 80%)
resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  alarm_name          = "${local.name_prefix}-ecs-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_ecs_memory_threshold
  alarm_description   = "Alerta quando memória do ECS ultrapassa o limite"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : []
}

# ─────────────────────────────────────────────────────────────────────────────
# CloudWatch Insights — Queries Salvas para Análise de Logs
# ─────────────────────────────────────────────────────────────────────────────

# Query: Erros por hora
resource "aws_cloudwatch_query_definition" "errors_by_hour" {
  name = "${local.name_prefix}-errors-by-hour"

  log_group_names = [aws_cloudwatch_log_group.ecs_api.name]

  query_string = <<-QUERY
    fields @timestamp, @message, @logStream
    | filter @message like /ERROR|Exception|error/
    | stats count() as error_count by bin(5m)
  QUERY
}

# Query: Latência de requisições
resource "aws_cloudwatch_query_definition" "request_latency" {
  name = "${local.name_prefix}-request-latency"

  log_group_names = [aws_cloudwatch_log_group.ecs_api.name]

  query_string = <<-QUERY
    fields @duration
    | filter @duration > 0
    | stats avg(@duration) as avg_latency, max(@duration) as max_latency, pct(@duration, 95) as p95_latency by @logStream
  QUERY
}

# Query: Taxa de erro por endpoint
resource "aws_cloudwatch_query_definition" "errors_by_endpoint" {
  name = "${local.name_prefix}-errors-by-endpoint"

  log_group_names = [aws_cloudwatch_log_group.ecs_api.name]

  query_string = <<-QUERY
    fields @timestamp, @message, path, status
    | filter status >= 400
    | stats count() as error_count by path, status
    | sort error_count desc
  QUERY
}

# Query: Performance de modelos ML
resource "aws_cloudwatch_query_definition" "model_performance" {
  name = "${local.name_prefix}-model-performance"

  log_group_names = [aws_cloudwatch_log_group.ecs_api.name]

  query_string = <<-QUERY
    fields @timestamp, model_name, prediction_time, accuracy, rmse
    | filter ispresent(model_name)
    | stats avg(prediction_time) as avg_pred_time, avg(accuracy) as avg_accuracy, avg(rmse) as avg_rmse by model_name
  QUERY
}

# Query: Sincronização de modelos
resource "aws_cloudwatch_query_definition" "model_sync" {
  name = "${local.name_prefix}-model-sync"

  log_group_names = [aws_cloudwatch_log_group.ecs_api.name]

  query_string = <<-QUERY
    fields @timestamp, @message, stage, model_version, sync_status
    | filter @message like /sync|promotion|champion|challenger/
    | stats count() as sync_count by stage, sync_status
  QUERY
}

# ─────────────────────────────────────────────────────────────────────────────
# CloudWatch Dashboard — Visualização de Métricas
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", { stat = "Average" }],
            [".", "HTTPCode_Target_5XX_Count", { stat = "Sum" }],
            [".", "HTTPCode_Target_4XX_Count", { stat = "Sum" }],
            ["AWS/ECS", "CPUUtilization", { stat = "Average" }],
            [".", "MemoryUtilization", { stat = "Average" }],
          ]
          period = 300
          stat   = "Average"
          region = data.aws_caller_identity.current.region
          title  = "Performance Overview"
        }
      },
      {
        type = "log"
        properties = {
          query   = "fields @timestamp, @message | filter @message like /ERROR/ | stats count() by bin(5m)"
          region  = data.aws_caller_identity.current.region
          title   = "Errors per 5 minutes"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "HealthyHostCount", { stat = "Average" }],
            [".", "UnHealthyHostCount", { stat = "Average" }],
          ]
          period = 60
          stat   = "Average"
          region = data.aws_caller_identity.current.region
          title  = "Target Health"
        }
      },
    ]
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Data Source — Informações da Conta AWS
# ─────────────────────────────────────────────────────────────────────────────
data "aws_caller_identity" "current" {}
