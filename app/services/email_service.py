import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

class EmailService:
    @staticmethod
    def send_daily_report(alerts):
        if not alerts: return

        sender_email = settings.FROM_EMAIL
        receiver_email = settings.ALERT_TO_EMAIL
        password = settings.RESEND_API_KEY

        subject = f"🚀 Stock Analyst Report - {len(alerts)} הזדמנויות חמות"

        html_content = """
        <html>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f0f2f5; padding: 20px; direction: rtl; text-align: right;">
                <div style="max-width: 650px; margin: auto;">
                    <h1 style="color: #1a73e8; text-align: center; font-size: 28px;">דוח איתותים מבוסס AI</h1>
        """

        for alert in alerts:
            ticker = alert.get('ticker')
            price = alert.get('price', 0)
            score = alert.get('score', 0)
            reasons = alert.get('reasons', [])
            ai_report = alert.get('ai_report', "ניתוח לא זמין")
            support = alert.get('support', price * 0.95)

            html_content += f"""
            <div style="background: white; border-radius: 15px; padding: 25px; margin-bottom: 30px; border: 1px solid #e1e4e8; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                <div style="border-bottom: 2px solid #f0f2f5; padding-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
                    <h2 style="margin: 0; color: #1a73e8; font-size: 24px;">{ticker}</h2>
                    <span style="background: #27ae60; color: white; padding: 6px 18px; border-radius: 25px; font-weight: bold;">Score: {score}/5</span>
                </div>

                <div style="margin-top: 20px;">
                    <table style="width: 100%; background: #f8f9fa; border-radius: 10px; padding: 15px;">
                        <tr>
                            <td><b>מחיר:</b> ${price:.2f}</td>
                            <td style="color: #d93025;"><b>סטופ:</b> ${support:.2f}</td>
                            <td style="color: #188038;"><b>יעד:</b> ${(price*1.15):.2f}</td>
                        </tr>
                    </table>
                </div>

                <div style="margin-top: 20px; padding: 18px; background: #fffde7; border-right: 5px solid #fbc02d; border-radius: 4px;">
                    <h3 style="margin: 0 0 10px 0; color: #f9a825; font-size: 18px;">🤖 ניתוח אנליסט (AI + Fundamentals):</h3>
                    <div style="font-size: 15px; line-height: 1.7; color: #2c3e50; white-space: pre-wrap;">{ai_report}</div>
                </div>

                <div style="margin-top: 20px;">
                    <h4 style="color: #5f6368; margin-bottom: 8px;">✅ אינדיקטורים טכניים שאותרו:</h4>
                    <ul style="padding-right: 20px; font-size: 14px; color: #34495e;">
                        {"".join([f"<li style='margin-bottom: 5px;'>{r}</li>" for r in reasons])}
                    </ul>
                </div>
            </div>
            """

        html_content += "</div></body></html>"

        message = MIMEMultipart()
        message["From"] = f"AI Trading Bot <{sender_email}>"
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP("smtp.resend.com", 587) as server:
                server.starttls()
                server.login("resend", password)
                server.send_message(message)
            print(f"📧 Professional AI report sent for {len(alerts)} tickers!")
        except Exception as e:
            print(f"❌ Email error: {e}")