package mailer

import (
	"crypto/tls"
	"fmt"
	"net/smtp"
	"strings"
)

type SMTPMailer struct {
	host      string
	port      int
	user      string
	password  string
	fromName  string
	fromEmail string
}

func NewSMTPMailer(host string, port int, user, password, fromName, fromEmail string) *SMTPMailer {
	return &SMTPMailer{
		host:      host,
		port:      port,
		user:      user,
		password:  password,
		fromName:  fromName,
		fromEmail: fromEmail,
	}
}

func (m *SMTPMailer) SendMail(toEmail, subject, htmlBody string) error {
	addr := fmt.Sprintf("%s:%d", m.host, m.port)
	fromHeader := fmt.Sprintf("%s <%s>", m.fromName, m.fromEmail)

	headers := make(map[string]string)
	headers["From"] = fromHeader
	headers["To"] = toEmail
	headers["Subject"] = subject
	headers["MIME-Version"] = "1.0"
	headers["Content-Type"] = "text/html; charset=\"UTF-8\""

	message := ""
	for k, v := range headers {
		message += fmt.Sprintf("%s: %s\r\n", k, v)
	}
	message += "\r\n" + htmlBody

	auth := smtp.PlainAuth("", m.user, m.password, m.host)

	// Direct SSL/TLS connection (Required for Port 465 on Hostinger)
	tlsConfig := &tls.Config{
		InsecureSkipVerify: false,
		ServerName:         m.host,
	}

	conn, err := tls.Dial("tcp", addr, tlsConfig)
	if err != nil {
		return fmt.Errorf("tls connection failed to %s: %w", addr, err)
	}
	defer conn.Close()

	client, err := smtp.NewClient(conn, m.host)
	if err != nil {
		return fmt.Errorf("failed to initialize smtp client: %w", err)
	}
	defer client.Quit()

	if err = client.Auth(auth); err != nil {
		return fmt.Errorf("smtp authentication failed for user %s: %w", m.user, err)
	}

	if err = client.Mail(m.fromEmail); err != nil {
		return fmt.Errorf("smtp MAIL command failed: %w", err)
	}

	if err = client.Rcpt(toEmail); err != nil {
		return fmt.Errorf("smtp RCPT command failed for %s: %w", toEmail, err)
	}

	w, err := client.Data()
	if err != nil {
		return fmt.Errorf("smtp DATA command failed: %w", err)
	}

	_, err = w.Write([]byte(message))
	if err != nil {
		return fmt.Errorf("failed to write email body: %w", err)
	}

	err = w.Close()
	if err != nil {
		return fmt.Errorf("failed to close data writer: %w", err)
	}

	return nil
}

func (m *SMTPMailer) SendOTPEmail(toEmail, toName, otpCode, purposeTitle string) error {
	if m == nil {
		return nil
	}
	subject := fmt.Sprintf("[%s] Your Verification Code: %s", m.fromName, otpCode)
	body := fmt.Sprintf(`
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0d1117; color: #e6edf3; padding: 20px; }
    .container { max-width: 540px; margin: 0 auto; background: #161b22; border-radius: 12px; border: 1px solid #30363d; padding: 32px; }
    .header { font-size: 22px; font-weight: 700; color: #58a6ff; letter-spacing: 1px; margin-bottom: 20px; }
    .otp-box { background: #21262d; border: 2px solid #58a6ff; border-radius: 8px; font-size: 32px; font-weight: 800; letter-spacing: 8px; text-align: center; color: #ffffff; padding: 18px 0; margin: 24px 0; }
    .info { font-size: 14px; color: #8b949e; line-height: 1.6; }
    .footer { font-size: 12px; color: #484f58; margin-top: 28px; text-align: center; border-top: 1px solid #21262d; padding-top: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">VĀSTU / NAMMA SPACE</div>
    <p style="font-size: 16px; color: #f0f6fc;">Hello <strong>%s</strong>,</p>
    <p class="info">Please use the following 6-digit verification code to complete your <strong>%s</strong>. This code is valid for <strong>10 minutes</strong>.</p>
    
    <div class="otp-box">%s</div>
    
    <p class="info">If you did not request this verification code, please ignore this email or contact support if you have concerns.</p>
    
    <div class="footer">
      VĀSTU Indoor Spatial Computing Platform &bull; Automated Delivery
    </div>
  </div>
</body>
</html>
`, toName, purposeTitle, otpCode)

	return m.SendMail(toEmail, subject, strings.TrimSpace(body))
}

func (m *SMTPMailer) SendAdminJoinAlert(adminEmail, adminName, memberName, memberEmail, orgName string) error {
	if m == nil {
		return nil
	}
	subject := fmt.Sprintf("[%s] New Join Request for %s", m.fromName, orgName)
	body := fmt.Sprintf(`
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0d1117; color: #e6edf3; padding: 20px; }
    .container { max-width: 540px; margin: 0 auto; background: #161b22; border-radius: 12px; border: 1px solid #30363d; padding: 32px; }
    .header { font-size: 20px; font-weight: 700; color: #f0883e; margin-bottom: 20px; }
    .member-box { background: #21262d; border-radius: 8px; padding: 16px; margin: 20px 0; }
    .member-item { font-size: 14px; margin: 6px 0; color: #c9d1d9; }
    .member-item strong { color: #f0f6fc; }
    .info { font-size: 14px; color: #8b949e; line-height: 1.6; }
    .footer { font-size: 12px; color: #484f58; margin-top: 28px; text-align: center; border-top: 1px solid #21262d; padding-top: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">Membership Access Request</div>
    <p style="font-size: 16px; color: #f0f6fc;">Hello <strong>%s</strong>,</p>
    <p class="info">A team member has requested access to join your organization <strong>%s</strong>:</p>
    
    <div class="member-box">
      <div class="member-item"><strong>Full Name:</strong> %s</div>
      <div class="member-item"><strong>Work Email:</strong> %s</div>
      <div class="member-item"><strong>Status:</strong> Pending Admin Approval</div>
    </div>
    
    <p class="info">Please log into your VĀSTU Organization Dashboard to review and approve or reject this request.</p>
    
    <div class="footer">
      VĀSTU Indoor Spatial Computing Platform &bull; Organization Access Control
    </div>
  </div>
</body>
</html>
`, adminName, orgName, memberName, memberEmail)

	return m.SendMail(adminEmail, subject, strings.TrimSpace(body))
}

func (m *SMTPMailer) SendMemberApprovalNotice(toEmail, toName, orgName string, approved bool, assignedRole string) error {
	if m == nil {
		return nil
	}
	statusText := "Approved"
	color := "#3fb950"
	if !approved {
		statusText = "Declined"
		color = "#f85149"
	}

	subject := fmt.Sprintf("[%s] Membership %s for %s", m.fromName, statusText, orgName)
	body := fmt.Sprintf(`
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0d1117; color: #e6edf3; padding: 20px; }
    .container { max-width: 540px; margin: 0 auto; background: #161b22; border-radius: 12px; border: 1px solid #30363d; padding: 32px; }
    .status-badge { font-size: 20px; font-weight: 700; color: %s; margin-bottom: 20px; }
    .info { font-size: 14px; color: #8b949e; line-height: 1.6; }
    .footer { font-size: 12px; color: #484f58; margin-top: 28px; text-align: center; border-top: 1px solid #21262d; padding-top: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="status-badge">Membership Request %s</div>
    <p style="font-size: 16px; color: #f0f6fc;">Hello <strong>%s</strong>,</p>
    <p class="info">Your request to join <strong>%s</strong> has been <strong>%s</strong>.</p>
    %s
    <div class="footer">
      VĀSTU Indoor Spatial Computing Platform
    </div>
  </div>
</body>
</html>
`, color, statusText, toName, orgName, statusText, func() string {
		if approved {
			return fmt.Sprintf(`<p class="info">Your assigned role is: <strong>%s</strong>. You can now access the organization digital twins and workspaces.</p>`, assignedRole)
		}
		return `<p class="info">Please contact your organization administrator if you believe this was in error.</p>`
	}())

	return m.SendMail(toEmail, subject, strings.TrimSpace(body))
}
