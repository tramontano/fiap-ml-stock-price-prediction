# =============================================================================
# Módulo: TLS — AWS Certificate Manager, HTTPS e Redirect HTTP
#
# Este módulo gerencia:
#   • Certificados SSL/TLS via AWS Certificate Manager (ACM)
#   • Listeners HTTPS no ALB (porta 443)
#   • Redirect automático de HTTP (80) → HTTPS (443)
#   • Validação de domínio (DNS ou Email)
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(var.tags, {
    Module      = "tls"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# AWS Certificate Manager — Certificado SSL/TLS
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_acm_certificate" "main" {
  domain_name       = var.domain_name
  validation_method = var.validation_method  # "DNS" ou "EMAIL"

  subject_alternative_names = var.subject_alternative_names

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-cert"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Validação DNS do Certificado (Automática se usar Route53)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_acm_certificate_validation" "main" {
  count = var.validation_method == "DNS" ? 1 : 0

  certificate_arn           = aws_acm_certificate.main.arn
  timeouts {
    create = "5m"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# ALB Listener HTTPS (Porta 443)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_lb_listener" "https" {
  load_balancer_arn = var.alb_arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = var.ssl_policy
  certificate_arn   = aws_acm_certificate.main.arn

  default_action {
    type             = "forward"
    target_group_arn = var.target_group_arn
  }

  depends_on = [
    var.validation_method == "DNS" ? aws_acm_certificate_validation.main[0] : aws_acm_certificate.main
  ]
}

# ─────────────────────────────────────────────────────────────────────────────
# ALB Listener HTTP (Porta 80) — Redirect para HTTPS
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = var.alb_arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"  # Permanent redirect
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Security Group — Permitir HTTPS (443) e HTTP (80) no ALB
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_security_group_rule" "alb_https_ingress" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = var.alb_security_group_id
  description       = "Allow HTTPS (443) from anywhere"
}

resource "aws_security_group_rule" "alb_http_ingress" {
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = var.alb_security_group_id
  description       = "Allow HTTP (80) from anywhere for redirect"
}

# ─────────────────────────────────────────────────────────────────────────────
# Data Source — Informações da Conta AWS
# ─────────────────────────────────────────────────────────────────────────────
data "aws_caller_identity" "current" {}
