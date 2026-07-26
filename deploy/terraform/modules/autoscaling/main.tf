# =============================================================================
# Módulo: Auto Scaling — Escalabilidade Avançada baseada em Múltiplas Métricas
#
# Este módulo configura:
#   • Target Tracking Scaling (CPU, Memória, ALB Request Count)
#   • Step Scaling para picos extremos
#   • Cooldown periods otimizados
#   • Métricas customizadas
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(var.tags, {
    Module      = "autoscaling"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Auto Scaling Target — Define min/max capacity
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${var.ecs_cluster_name}/${var.ecs_service_name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-asg-target"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Policy 1: CPU Utilization (Target Tracking)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_appautoscaling_policy" "cpu_scaling" {
  name               = "${local.name_prefix}-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.cpu_target_utilization
    scale_in_cooldown  = var.scale_in_cooldown
    scale_out_cooldown = var.scale_out_cooldown
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Policy 2: Memory Utilization (Target Tracking)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_appautoscaling_policy" "memory_scaling" {
  count              = var.enable_memory_scaling ? 1 : 0
  name               = "${local.name_prefix}-memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = var.memory_target_utilization
    scale_in_cooldown  = var.scale_in_cooldown
    scale_out_cooldown = var.scale_out_cooldown
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Policy 3: ALB Request Count per Target (Target Tracking)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_appautoscaling_policy" "alb_request_count_scaling" {
  count              = var.enable_alb_request_scaling ? 1 : 0
  name               = "${local.name_prefix}-alb-request-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = var.alb_resource_label  # ex: "app/my-alb/1234567890abcdef/targetgroup/my-targets/1234567890abcdef"
    }
    target_value       = var.alb_request_count_target
    scale_in_cooldown  = var.scale_in_cooldown
    scale_out_cooldown = var.scale_out_cooldown
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Policy 4: Custom Metric Scaling (Opcional - para métricas do CloudWatch)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_appautoscaling_policy" "custom_metric_scaling" {
  count              = var.enable_custom_metric_scaling ? 1 : 0
  name               = "${local.name_prefix}-custom-metric-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    customized_metric_specification {
      metric_name = var.custom_metric_name
      namespace   = var.custom_metric_namespace
      statistic   = var.custom_metric_statistic
      unit        = var.custom_metric_unit
    }
    target_value       = var.custom_metric_target_value
    scale_in_cooldown  = var.scale_in_cooldown
    scale_out_cooldown = var.scale_out_cooldown
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Step Scaling Policy (Para picos extremos)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "cpu_high_extreme" {
  count               = var.enable_step_scaling ? 1 : 0
  alarm_name          = "${local.name_prefix}-cpu-extreme-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = var.step_scaling_cpu_threshold  # ex: 90%
  alarm_description   = "Alarme para step scaling quando CPU fica muito alta"
  alarm_actions       = [aws_appautoscaling_policy.step_scaling[0].arn]

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }
}

resource "aws_appautoscaling_policy" "step_scaling" {
  count              = var.enable_step_scaling ? 1 : 0
  name               = "${local.name_prefix}-step-scaling"
  policy_type        = "StepScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  step_scaling_policy_configuration {
    adjustment_type          = "ChangeInCapacity"
    cooldown                 = var.step_scaling_cooldown
    metric_aggregation_type  = "Average"

    # Escalas em degraus: +2 instâncias se CPU > 90%, +4 se > 95%
    step_adjustment {
      metric_interval_lower_bound = 0
      metric_interval_upper_bound = 5
      scaling_adjustment          = 2
    }

    step_adjustment {
      metric_interval_lower_bound = 5
      scaling_adjustment          = 4
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Data Source — Informações da Conta AWS
# ─────────────────────────────────────────────────────────────────────────────
data "aws_caller_identity" "current" {}
