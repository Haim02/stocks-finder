# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from app.core.config import settings

# class EmailService:
#     @staticmethod
#     def send_daily_report(alerts):
#         if not alerts: return

#         sender_email = settings.FROM_EMAIL
#         receiver_email = settings.ALERT_TO_EMAIL
#         password = settings.RESEND_API_KEY

#         subject = f"🚀 Stock Analyst Report - {len(alerts)} הזדמנויות חמות"

#         html_content = """
#         <html>
#             <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f0f2f5; padding: 20px; direction: rtl; text-align: right;">
#                 <div style="max-width: 650px; margin: auto;">
#                     <h1 style="color: #1a73e8; text-align: center; font-size: 28px;">דוח איתותים מבוסס AI</h1>
#         """

#         for alert in alerts:
#             ticker = alert.get('ticker')
#             price = alert.get('price', 0)
#             score = alert.get('score', 0)
#             reasons = alert.get('reasons', [])
#             ai_report = alert.get('ai_report', "ניתוח לא זמין")
#             support = alert.get('support', price * 0.95)

#             html_content += f"""
#             <div style="background: white; border-radius: 15px; padding: 25px; margin-bottom: 30px; border: 1px solid #e1e4e8; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
#                 <div style="border-bottom: 2px solid #f0f2f5; padding-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
#                     <h2 style="margin: 0; color: #1a73e8; font-size: 24px;">{ticker}</h2>
#                     <span style="background: #27ae60; color: white; padding: 6px 18px; border-radius: 25px; font-weight: bold;">Score: {score}/5</span>
#                 </div>

#                 <div style="margin-top: 20px;">
#                     <table style="width: 100%; background: #f8f9fa; border-radius: 10px; padding: 15px;">
#                         <tr>
#                             <td><b>מחיר:</b> ${price:.2f}</td>
#                             <td style="color: #d93025;"><b>סטופ:</b> ${support:.2f}</td>
#                             <td style="color: #188038;"><b>יעד:</b> ${(price*1.15):.2f}</td>
#                         </tr>
#                     </table>
#                 </div>

#                 <div style="margin-top: 20px; padding: 18px; background: #fffde7; border-right: 5px solid #fbc02d; border-radius: 4px;">
#                     <h3 style="margin: 0 0 10px 0; color: #f9a825; font-size: 18px;">🤖 ניתוח אנליסט (AI + Fundamentals):</h3>
#                     <div style="font-size: 15px; line-height: 1.7; color: #2c3e50; white-space: pre-wrap;">{ai_report}</div>
#                 </div>

#                 <div style="margin-top: 20px;">
#                     <h4 style="color: #5f6368; margin-bottom: 8px;">✅ אינדיקטורים טכניים שאותרו:</h4>
#                     <ul style="padding-right: 20px; font-size: 14px; color: #34495e;">
#                         {"".join([f"<li style='margin-bottom: 5px;'>{r}</li>" for r in reasons])}
#                     </ul>
#                 </div>
#             </div>
#             """

#         html_content += "</div></body></html>"

#         message = MIMEMultipart()
#         message["From"] = f"AI Trading Bot <{sender_email}>"
#         message["To"] = receiver_email
#         message["Subject"] = subject
#         message.attach(MIMEText(html_content, "html"))

#         try:
#             with smtplib.SMTP("smtp.resend.com", 587) as server:
#                 server.starttls()
#                 server.login("resend", password)
#                 server.send_message(message)
#             print(f"📧 Professional AI report sent for {len(alerts)} tickers!")
#         except Exception as e:
#             print(f"❌ Email error: {e}")


# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from app.core.config import settings

# class EmailService:
#     @staticmethod
#     def send_daily_report(alerts):
#         if not alerts: return

#         sender_email = settings.FROM_EMAIL
#         receiver_email = settings.ALERT_TO_EMAIL
#         password = settings.RESEND_API_KEY

#         subject = f"🚀 Stock Report - {len(alerts)} חברות מעניינות אותרו"

#         html_content = """
#         <html>
#             <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f0f2f5; padding: 20px; direction: rtl; text-align: right;">
#                 <div style="max-width: 650px; margin: auto;">
#                     <h1 style="color: #1a73e8; text-align: center; font-size: 28px;">דוח אנליסט AI יומי</h1>
#         """

#         for alert in alerts:
#             ticker = alert.get('ticker')
#             company_name = alert.get('company_name', ticker)
#             industry = alert.get('industry', 'N/A')
#             price = alert.get('price', 0)
#             score = alert.get('score', 0)
#             ai_report = alert.get('ai_report', "ניתוח לא זמין")

#             html_content += f"""
#             <div style="background: white; border-radius: 15px; padding: 25px; margin-bottom: 30px; border: 1px solid #e1e4e8; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
#                 <div style="border-bottom: 2px solid #f0f2f5; padding-bottom: 15px;">
#                     <h2 style="margin: 0; color: #1a73e8; font-size: 22px;">{company_name} ({ticker})</h2>
#                     <p style="margin: 5px 0; color: #5f6368;">סקטור: {industry}</p>
#                     <span style="background: #27ae60; color: white; padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: bold;">Score: {score}/5</span>
#                 </div>

#                 <div style="margin-top: 20px; padding: 18px; background: #fffde7; border-right: 5px solid #fbc02d; border-radius: 4px;">
#                     <div style="font-size: 15px; line-height: 1.7; color: #2c3e50; white-space: pre-wrap;">{ai_report}</div>
#                 </div>
#             </div>
#             """

#         html_content += "</div></body></html>"

#         message = MIMEMultipart()
#         message["From"] = f"Stock AI Analyst <{sender_email}>"
#         message["To"] = receiver_email
#         message["Subject"] = subject
#         message.attach(MIMEText(html_content, "html"))

#         try:
#             with smtplib.SMTP("smtp.resend.com", 587) as server:
#                 server.starttls()
#                 server.login("resend", password)
#                 server.send_message(message)
#             print(f"📧 Report sent for {len(alerts)} tickers!")
#         except Exception as e:
#             print(f"❌ Email error: {e}")



# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from app.core.config import settings

# class EmailService:
#     @staticmethod
#     def send_daily_report(alerts):
#         if not alerts: return

#         sender_email = settings.FROM_EMAIL
#         receiver_email = settings.ALERT_TO_EMAIL
#         password = settings.RESEND_API_KEY

#         subject = f"🚀 Stock Report - {len(alerts)} חברות מעניינות אותרו"

#         # התחלת ה-HTML עם עיצוב כללי
#         html_content = """
#         <html>
#             <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f7f9; padding: 20px; direction: rtl; text-align: right;">
#                 <div style="max-width: 650px; margin: auto;">
#                     <h1 style="color: #1a73e8; text-align: center; font-size: 28px; margin-bottom: 30px;">דוח אנליסט AI יומי</h1>
#         """

#         for alert in alerts:
#             ticker = alert.get('ticker')
#             company_name = alert.get('company_name', ticker)
#             industry = alert.get('industry', 'N/A')
#             price = alert.get('price', 0)
#             score = alert.get('score', 0)
#             ai_report = alert.get('ai_report', "ניתוח לא זמין")

#             # חישוב יעד וסטופ גנריים רק להצגה בתיבת המחיר (ה-AI יתן מדויק בטבלה למטה)
#             stop_est = round(price * 0.95, 2)
#             target_est = round(price * 1.10, 2)

#             html_content += f"""
#             <div style="background: white; border-radius: 15px; padding: 0; margin-bottom: 40px; border: 1px solid #e1e4e8; box-shadow: 0 4px 15px rgba(0,0,0,0.08); overflow: hidden;">

#                 <div style="background: #1a73e8; color: white; padding: 15px 25px;">
#                     <h2 style="margin: 0; font-size: 22px;">{company_name} ({ticker}) | {industry}</h2>
#                 </div>

#                 <div style="display: flex; justify-content: space-around; background: #f8f9fa; padding: 15px; border-bottom: 1px solid #eee; text-align: center;">
#                     <div style="flex: 1;"><strong>מחיר:</strong><br>${price}</div>
#                     <div style="flex: 1; color: #d93025;"><strong>סטופ:</strong><br>${stop_est}</div>
#                     <div style="flex: 1; color: #1e8e3e;"><strong>יעד:</strong><br>${target_est}</div>
#                     <div style="flex: 1;"><strong>ציון:</strong><br>{score}/5</div>
#                 </div>

#                 <div style="padding: 25px; line-height: 1.7; color: #2c3e50;">
#                     {ai_report}
#                 </div>
#             </div>
#             """

#         html_content += """
#                     <p style="text-align: center; color: #9aa0a6; font-size: 12px; margin-top: 20px;">
#                         נשלח אוטומטית ע"י מערכת הניתוח שלך
#                     </p>
#                 </div>
#             </body>
#         </html>
#         """

#         message = MIMEMultipart()
#         message["From"] = f"Stock AI Analyst <{sender_email}>"
#         message["To"] = receiver_email
#         message["Subject"] = subject
#         message.attach(MIMEText(html_content, "html"))

#         try:
#             with smtplib.SMTP("smtp.resend.com", 587) as server:
#                 server.starttls()
#                 server.login("resend", password)
#                 server.send_message(message)
#             print(f"📧 Report sent for {len(alerts)} tickers!")
#         except Exception as e:
#             print(f"❌ Email error: {e}")


# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from app.core.config import settings

# class EmailService:
#     @staticmethod
#     def send_daily_report(alerts):
#         if not alerts: return

#         sender_email = settings.FROM_EMAIL
#         receiver_email = settings.ALERT_TO_EMAIL
#         password = settings.RESEND_API_KEY

#         subject = f"🚀 דוח פריצה יומי - {len(alerts)} הזדמנויות אותרו"

#         html_content = """
#         <html>
#             <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f7f9; padding: 20px; direction: rtl; text-align: right;">
#                 <div style="max-width: 650px; margin: auto;">
#                     <h1 style="color: #1a73e8; text-align: center; font-size: 28px; margin-bottom: 30px;">דוח אנליסט AI יומי</h1>
#         """

#         for alert in alerts:
#             ticker = alert.get('ticker')
#             company_name = alert.get('company_name', ticker)
#             industry = alert.get('industry', 'N/A')
#             price = alert.get('price', 0)
#             score = alert.get('score', 0)
#             ai_report = alert.get('ai_report', "ניתוח לא זמין")

#             # --- לוגיקה חכמה למטרות (Targets) ---
#             # לוקחים את התמיכה שהמנוע מצא. אם אין, שמים סטופ ב-7% (סטנדרט לסווינג)
#             support = alert.get('support', price * 0.93)

#             # סטופ לוס: 1% מתחת לתמיכה כדי להימנע מ"רעשים"
#             stop_price = round(support * 0.99, 2)

#             # חישוב הסיכון בדולרים
#             risk_per_share = price - stop_price
#             if risk_per_share <= 0: risk_per_share = price * 0.05 # הגנה למקרה של תקלה בנתונים

#             # יעד רווח: יחס סיכון/סיכוי של 1:2.5 (נחשב ליחס מעולה בסווינג)
#             target_price = round(price + (risk_per_share * 2.5), 2)

#             html_content += f"""
#             <div style="background: white; border-radius: 15px; padding: 0; margin-bottom: 40px; border: 1px solid #e1e4e8; box-shadow: 0 4px 15px rgba(0,0,0,0.08); overflow: hidden;">

#                 <div style="background: #1a73e8; color: white; padding: 15px 25px;">
#                     <h2 style="margin: 0; font-size: 22px;">{company_name} ({ticker}) | {industry}</h2>
#                 </div>

#                 <div style="display: flex; justify-content: space-around; background: #f8f9fa; padding: 15px; border-bottom: 1px solid #eee; text-align: center;">
#                     <div style="flex: 1;"><strong>מחיר כניסה:</strong><br>${price}</div>
#                     <div style="flex: 1; color: #d93025;"><strong>סטופ לוס:</strong><br>${stop_price}</div>
#                     <div style="flex: 1; color: #1e8e3e;"><strong>יעד רווח:</strong><br>${target_price}</div>
#                     <div style="flex: 1;"><strong>ציון:</strong><br>{score}/5</div>
#                 </div>

#                 <div style="padding: 25_px; line-height: 1.7; color: #2c3e50;">
#                     {ai_report}
#                 </div>
#             </div>
#             """

#         html_content += """
#                     <p style="text-align: center; color: #9aa0a6; font-size: 12px; margin-top: 20px;">
#                         נשלח אוטומטית ע"י מערכת הניתוח שלך | Risk/Reward 1:2.5
#                     </p>
#                 </div>
#             </body>
#         </html>
#         """

#         message = MIMEMultipart()
#         message["From"] = f"Stock AI Analyst <{sender_email}>"
#         message["To"] = receiver_email
#         message["Subject"] = subject
#         message.attach(MIMEText(html_content, "html"))

#         try:
#             with smtplib.SMTP("smtp.resend.com", 587) as server:
#                 server.starttls()
#                 server.login("resend", password)
#                 server.send_message(message)
#             print(f"📧 Report sent for {len(alerts)} tickers with smart targets!")
#         except Exception as e:
#             print(f"❌ Email error: {e}")



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

        subject = f"🚀 הזדמנויות מסחר מוקדמות - {len(alerts)} מניות אותרו"

        html_content = """
        <html dir="rtl">
            <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px;">
                <div style="max-width: 600px; margin: auto;">
                    <h1 style="color: #1a73e8; text-align: center; font-size: 24px; margin-bottom: 25px;">דוח אנליסט AI - איתותים מוקדמים</h1>
        """

        for alert in alerts:
            ticker = alert.get('ticker')
            company_name = alert.get('company_name', ticker)
            industry = alert.get('industry', 'N/A')
            price = alert.get('price', 0)
            score = alert.get('score', 0)
            ai_report = alert.get('ai_report', "ניתוח לא זמין")

            # --- חישוב ניהול סיכונים ---
            support = alert.get('support', price * 0.95)
            stop_price = round(support * 0.99, 2) # קצת מתחת לתמיכה

            risk = price - stop_price
            if risk <= 0: risk = price * 0.04 # ברירת מחדל אם יש בעיה בנתונים

            target_price = round(price + (risk * 2.5), 2) # יחס 1:2.5

            html_content += f"""
            <div style="background: white; border-radius: 12px; margin-bottom: 35px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid #e1e4e8;">

                <div style="background: #1a73e8; color: white; padding: 15px 20px;">
                    <h2 style="margin: 0; font-size: 20px;">{ticker} | {company_name}</h2>
                    <div style="font-size: 13px; opacity: 0.9;">{industry}</div>
                </div>

                <div style="display: flex; justify-content: space-between; background: #f8f9fa; padding: 15px 20px; border-bottom: 1px solid #eee; text-align: center;">
                    <div>
                        <span style="font-size: 12px; color: #666;">מחיר</span><br>
                        <strong>${price}</strong>
                    </div>
                    <div>
                        <span style="font-size: 12px; color: #d32f2f;">סטופ (Risk)</span><br>
                        <strong style="color: #d32f2f;">${stop_price}</strong>
                    </div>
                    <div>
                        <span style="font-size: 12px; color: #2e7d32;">יעד (Reward)</span><br>
                        <strong style="color: #2e7d32;">${target_price}</strong>
                    </div>
                    <div>
                        <span style="font-size: 12px; color: #666;">דירוג</span><br>
                        <strong>{score}/5</strong>
                    </div>
                </div>

                <div style="padding: 25px; line-height: 1.6; color: #333; font-size: 15px;">
                    {ai_report}
                </div>
            </div>
            """

        html_content += """
                    <div style="text-align: center; color: #888; font-size: 12px; margin-top: 30px;">
                        <p>המערכת מחפשת דחיסות ופריצות מוקדמות • יחס סיכון/סיכוי מומלץ 1:2.5</p>
                    </div>
                </div>
            </body>
        </html>
        """

        message = MIMEMultipart()
        message["From"] = f"Stock AI Analyst <{sender_email}>"
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP("smtp.resend.com", 587) as server:
                server.starttls()
                server.login("resend", password)
                server.send_message(message)
            print(f"📧 Report sent successfully for {len(alerts)} tickers!")
        except Exception as e:
            print(f"❌ Email error: {e}")