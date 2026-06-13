# =============================================================================
# Módulo: IAM — Outputs
# =============================================================================

output "ecs_execution_role_arn" {
  description = "ARN da Execution Role do ECS (pull ECR, logs, secrets)."
  value       = aws_iam_role.ecs_execution.arn
}

output "ecs_task_role_arn" {
  description = "ARN da Task Role do ECS (permissões da aplicação FastAPI)."
  value       = aws_iam_role.ecs_task.arn
}

output "ecs_execution_role_name" {
  description = "Nome da Execution Role do ECS."
  value       = aws_iam_role.ecs_execution.name
}

output "ecs_task_role_name" {
  description = "Nome da Task Role do ECS."
  value       = aws_iam_role.ecs_task.name
}
