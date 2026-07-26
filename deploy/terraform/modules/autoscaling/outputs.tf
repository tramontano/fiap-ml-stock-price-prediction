# =============================================================================
# Módulo: Auto Scaling — Outputs
# =============================================================================

output "autoscaling_target_arn" {
  description = "ARN do Auto Scaling Target."
  value       = aws_appautoscaling_target.ecs_target.arn
}

output "cpu_scaling_policy_arn" {
  description = "ARN da política de CPU scaling."
  value       = aws_appautoscaling_policy.cpu_scaling.arn
}

output "memory_scaling_policy_arn" {
  description = "ARN da política de memory scaling (se habilitada)."
  value       = try(aws_appautoscaling_policy.memory_scaling[0].arn, null)
}

output "alb_request_scaling_policy_arn" {
  description = "ARN da política de ALB request count scaling (se habilitada)."
  value       = try(aws_appautoscaling_policy.alb_request_count_scaling[0].arn, null)
}

output "custom_metric_scaling_policy_arn" {
  description = "ARN da política de custom metric scaling (se habilitada)."
  value       = try(aws_appautoscaling_policy.custom_metric_scaling[0].arn, null)
}

output "step_scaling_policy_arn" {
  description = "ARN da política de step scaling (se habilitada)."
  value       = try(aws_appautoscaling_policy.step_scaling[0].arn, null)
}

output "scaling_policies" {
  description = "Mapa de todas as políticas de scaling ativas."
  value = {
    cpu_scaling                = aws_appautoscaling_policy.cpu_scaling.name
    memory_scaling             = try(aws_appautoscaling_policy.memory_scaling[0].name, null)
    alb_request_count_scaling  = try(aws_appautoscaling_policy.alb_request_count_scaling[0].name, null)
    custom_metric_scaling      = try(aws_appautoscaling_policy.custom_metric_scaling[0].name, null)
    step_scaling               = try(aws_appautoscaling_policy.step_scaling[0].name, null)
  }
}
