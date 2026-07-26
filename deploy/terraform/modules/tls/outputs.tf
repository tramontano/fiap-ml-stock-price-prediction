# =============================================================================
# Módulo: TLS — Outputs
# =============================================================================

output "certificate_arn" {
  description = "ARN do certificado ACM."
  value       = aws_acm_certificate.main.arn
}

output "certificate_domain_name" {
  description = "Nome do domínio do certificado."
  value       = aws_acm_certificate.main.domain_name
}

output "certificate_status" {
  description = "Status do certificado ACM (PENDING_VALIDATION, ISSUED, INACTIVE, EXPIRED, VALIDATION_TIMED_OUT, REVOKED)."
  value       = aws_acm_certificate.main.status
}

output "https_listener_arn" {
  description = "ARN do listener HTTPS (porta 443)."
  value       = aws_lb_listener.https.arn
}

output "http_redirect_listener_arn" {
  description = "ARN do listener HTTP redirect (porta 80 → 443)."
  value       = aws_lb_listener.http_redirect.arn
}

output "certificate_validation_options" {
  description = "Opções de validação do certificado (para DNS records em Route53)."
  value       = aws_acm_certificate.main.domain_validation_options
  sensitive   = true
}
