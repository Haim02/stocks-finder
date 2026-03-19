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

#         subject = f"🚀 הזדמנויות מסחר מוקדמות - {len(alerts)} מניות אותרו"

#         html_content = """
#         <html dir="rtl">
#             <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px;">
#                 <div style="max-width: 600px; margin: auto;">
#                     <h1 style="color: #1a73e8; text-align: center; font-size: 24px; margin-bottom: 25px;">דוח אנליסט AI - איתותים מוקדמים</h1>
#         """

#         for alert in alerts:
#             ticker = alert.get('ticker')
#             company_name = alert.get('company_name', ticker)
#             industry = alert.get('industry', 'N/A')
#             price = alert.get('price', 0)
#             score = alert.get('score', 0)
#             ai_report = alert.get('ai_report', "ניתוח לא זמין")

#             # --- חישוב ניהול סיכונים ---
#             support = alert.get('support', price * 0.95)
#             stop_price = round(support * 0.99, 2) # קצת מתחת לתמיכה

#             risk = price - stop_price
#             if risk <= 0: risk = price * 0.04 # ברירת מחדל אם יש בעיה בנתונים

#             target_price = round(price + (risk * 2.5), 2) # יחס 1:2.5

#             html_content += f"""
#             <div style="background: white; border-radius: 12px; margin-bottom: 35px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid #e1e4e8;">

#                 <div style="background: #1a73e8; color: white; padding: 15px 20px;">
#                     <h2 style="margin: 0; font-size: 20px;">{ticker} | {company_name}</h2>
#                     <div style="font-size: 13px; opacity: 0.9;">{industry}</div>
#                 </div>

#                 <div style="display: flex; justify-content: space-between; background: #f8f9fa; padding: 15px 20px; border-bottom: 1px solid #eee; text-align: center;">
#                     <div>
#                         <span style="font-size: 12px; color: #666;">מחיר</span><br>
#                         <strong>${price}</strong>
#                     </div>
#                     <div>
#                         <span style="font-size: 12px; color: #d32f2f;">סטופ (Risk)</span><br>
#                         <strong style="color: #d32f2f;">${stop_price}</strong>
#                     </div>
#                     <div>
#                         <span style="font-size: 12px; color: #2e7d32;">יעד (Reward)</span><br>
#                         <strong style="color: #2e7d32;">${target_price}</strong>
#                     </div>
#                     <div>
#                         <span style="font-size: 12px; color: #666;">דירוג</span><br>
#                         <strong>{score}/5</strong>
#                     </div>
#                 </div>

#                 <div style="padding: 25px; line-height: 1.6; color: #333; font-size: 15px;">
#                     {ai_report}
#                 </div>
#             </div>
#             """

#         html_content += """
#                     <div style="text-align: center; color: #888; font-size: 12px; margin-top: 30px;">
#                         <p>המערכת מחפשת דחיסות ופריצות מוקדמות • יחס סיכון/סיכוי מומלץ 1:2.5</p>
#                     </div>
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
#             print(f"📧 Report sent successfully for {len(alerts)} tickers!")
#         except Exception as e:
#             print(f"❌ Email error: {e}")

# import resend
# from app.core.config import settings

# # הגדרת המפתח של Resend
# if settings.RESEND_API_KEY:
#     resend.api_key = settings.RESEND_API_KEY
# else:
#     print("⚠️ Warning: RESEND_API_KEY is missing from settings!")

# class EmailService:
#     @staticmethod
#     def send_report(opportunities):
#         if not opportunities:
#             return

#         # בדיקה שהגדרות המייל קיימות
#         if not settings.RESEND_API_KEY or not settings.ALERT_TO_EMAIL:
#             print("❌ Cannot send email: Missing RESEND_API_KEY or ALERT_TO_EMAIL.")
#             return

#         subject = f"🚀 Market Signals: {len(opportunities)} Stocks Found"

#         # --- בניית ה-HTML ---
#         html_body = """
#         <div dir="rtl" style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
#             <h2 style="background-color: #2c3e50; color: white; padding: 15px; border-radius: 8px; text-align: center;">
#                 דוח הזדמנויות יומי (AI Signals)
#             </h2>
#         """

#         for opp in opportunities:
#             fin = opp['financials']

#             # המרת שווי שוק
#             mcap = fin.get('market_cap', 0)
#             if mcap > 1000:
#                 market_cap_str = f"{mcap/1000:.1f}B"
#             else:
#                 market_cap_str = f"{mcap:.0f}M"

#             html_body += f"""
#             <div style="border:1px solid #e0e0e0; padding:20px; margin-bottom:20px; border-radius:10px; background-color: #ffffff; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">

#                 <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; margin-bottom: 15px;">
#                     <h3 style="color:#2980b9; margin: 0; font-size: 24px;">{opp['ticker']}</h3>
#                     <span style="background-color: #27ae60; color: white; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 14px;">
#                         ציון: {int(opp['score'])}
#                     </span>
#                 </div>

#                 <p style="font-size: 16px; line-height: 1.5; color: #444;">
#                     <b>📰 אירוע חדשותי:</b><br>
#                     {opp['headline']}
#                 </p>

#                 <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
#                     <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
#                         <span>💰 <b>מחיר כניסה:</b> ${opp['price']}</span>
#                         <span style="color: green;">🎯 <b>יעד:</b> ${fin['target_price']}</span>
#                         <span style="color: red;">🛑 <b>סטופ:</b> ${fin['stop_loss']}</span>
#                     </div>
#                 </div>

#                 <div style="font-size: 14px; color: #666; border-top: 1px solid #eee; padding-top: 10px;">
#                     <b>📊 נתונים פונדמנטליים:</b>
#                     <ul style="margin-top: 5px; padding-right: 20px;">
#                         <li>שווי שוק: <b>{market_cap_str}</b></li>
#                         <li>צמיחה בהכנסות: <b>{fin['revenue_growth']}%</b></li>
#                     </ul>
#                 </div>

#                 <div style="text-align: center; margin-top: 15px;">
#                     <a href="https://finviz.com/quote.ashx?t={opp['ticker']}" style="background-color: #3498db; color: white; text-decoration: none; padding: 8px 16px; border-radius: 5px; font-size: 14px;">👉 צפה בגרף ב-Finviz</a>
#                 </div>
#             </div>
#             """

#         html_body += """
#             <p style="text-align: center; color: #999; font-size: 12px; margin-top: 30px;">
#                 Generated by Stocks-Finder AI • Automated Report
#             </p>
#         </div>
#         """

#         # --- שליחה באמצעות Resend ---
#         try:
#             print(f"📧 Sending via Resend to {settings.ALERT_TO_EMAIL}...")

#             params = {
#                 "from": settings.FROM_EMAIL,      # חייב להיות דומיין מאומת או onboarding@resend.dev
#                 "to": [settings.ALERT_TO_EMAIL],  # המייל המקבל
#                 "subject": subject,
#                 "html": html_body,
#             }

#             email = resend.Emails.send(params)
#             print(f"✅ Email sent successfully! ID: {email.get('id')}")

#         except Exception as e:
#             print(f"❌ Resend API Error: {e}")


# import resend
# from app.core.config import settings

# if settings.RESEND_API_KEY:
#     resend.api_key = settings.RESEND_API_KEY

# class EmailService:
#     @staticmethod
#     def send_report(opportunities):
#         if not opportunities: return
#         if not settings.RESEND_API_KEY:
#             print("❌ Config Error: Missing RESEND_API_KEY.")
#             return

#         subject = f"🚀 AI Trade Report: {len(opportunities)} Stocks Analyzed"

#         html_body = """
#         <div dir="rtl" style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; max-width: 700px; margin: 0 auto; background-color: #f4f6f8; padding: 20px;">
#             <h2 style="background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 30px;">
#                 📊 דוח מסחר מבוסס AI
#             </h2>
#         """

#         for opp in opportunities:
#             fin = opp['financials']
#             eff = fin.get('efficiency')

#             # לוגיקה לתצוגת התייעלות
#             if eff:
#                 if eff['is_improving']:
#                     eff_icon = "🟢 משתפר"
#                     eff_bg = "#e8f5e9"
#                 else:
#                     eff_icon = "🔴 נחלש"
#                     eff_bg = "#ffebee"

#                 eff_row = f"""
#                 <tr style="background-color: {eff_bg};">
#                     <td style="padding: 8px;"><b>יחס התייעלות</b> (הוצאות/הכנסות)</td>
#                     <td style="padding: 8px;">{eff['curr_ratio']}%</td>
#                     <td style="padding: 8px;">{eff['prev_ratio']}%</td>
#                     <td style="padding: 8px; font-weight: bold;">{eff_icon}</td>
#                 </tr>
#                 """
#             else:
#                 eff_row = "<tr><td colspan='4' style='padding:8px;'>אין נתונים מספיקים לחישוב התייעלות</td></tr>"

#             # המרת שווי שוק
#             mcap = fin.get('market_cap', 0)
#             if mcap > 1_000_000_000:
#                 mcap_str = f"{mcap/1_000_000_000:.1f}B"
#             else:
#                 mcap_str = f"{mcap/1_000_000:.1f}M"

#             html_body += f"""
#             <div style="background-color: white; border-radius: 12px; padding: 25px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">

#                 <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 20px;">
#                     <div>
#                         <h1 style="color:#2c3e50; margin: 0; font-size: 28px;">{opp['ticker']} <span style="font-size:16px; color:#7f8c8d;">({mcap_str})</span></h1>
#                         <span style="color: #7f8c8d; font-size: 14px;">{fin.get('industry')}</span>
#                     </div>
#                     <div style="background-color: #27ae60; color: white; padding: 8px 15px; border-radius: 20px; font-weight: bold;">
#                         Score: {int(opp['score'])}
#                     </div>
#                 </div>

#                 <div style="background-color: #f9f9f9; padding: 12px; border-radius: 6px; font-size: 13px; color: #666; margin-bottom: 15px;">
#                     <b>🏢 פרופיל חברה:</b> {fin.get('description')}
#                 </div>

#                 <div style="margin-bottom: 20px;">
#                     <h3 style="margin: 0 0 5px 0; color: #d35400; font-size:16px;">📰 טריגר חדשותי:</h3>
#                     <p style="font-size: 15px; font-weight: 500; margin: 0;">{opp['headline']}</p>
#                 </div>

#                 <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; border-right: 4px solid #2196f3; margin-bottom: 20px;">
#                     <b style="color:#1565c0;">🤖 האנליסט של OpenAI:</b><br>
#                     <span style="font-size: 15px; line-height: 1.5;">{opp.get('ai_analysis', 'AI Processing Failed')}</span>
#                 </div>

#                 <h3 style="font-size:16px; border-bottom: 1px solid #eee; padding-bottom: 5px;">📈 ביצועים (רבעון מול רבעון)</h3>
#                 <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; text-align: right;">
#                     <tr style="background-color: #f1f1f1;">
#                         <th style="padding: 8px;">מדד</th>
#                         <th style="padding: 8px;">נוכחי</th>
#                         <th style="padding: 8px;">קודם</th>
#                         <th style="padding: 8px;">מגמה</th>
#                     </tr>
#                     <tr>
#                         <td style="padding: 8px; border-bottom: 1px solid #eee;"><b>צמיחה בהכנסות</b></td>
#                         <td style="padding: 8px; border-bottom: 1px solid #eee;" colspan="2">-</td>
#                         <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; color: {'green' if fin['revenue_growth_qoq'] > 0 else 'red'};">
#                             {fin['revenue_growth_qoq']}%
#                         </td>
#                     </tr>
#                     {eff_row}
#                 </table>

#                 <div style="display: flex; justify-content: space-between; margin-top: 25px; text-align: center; background-color: #fff8e1; padding: 15px; border-radius: 8px;">
#                     <div>
#                         <div style="font-size: 12px; color: #555;">מחיר כניסה</div>
#                         <div style="font-size: 18px; font-weight: bold;">${opp['price']}</div>
#                     </div>
#                     <div>
#                         <div style="font-size: 12px; color: green;">יעד (TP)</div>
#                         <div style="font-size: 18px; font-weight: bold; color: green;">${fin['target_price']}</div>
#                     </div>
#                     <div>
#                         <div style="font-size: 12px; color: red;">סטופ (SL)</div>
#                         <div style="font-size: 18px; font-weight: bold; color: red;">${fin['stop_loss']}</div>
#                     </div>
#                 </div>

#                 <div style="text-align: center; margin-top: 15px;">
#                     <a href="https://finviz.com/quote.ashx?t={opp['ticker']}" style="font-size:14px; color: #3498db; text-decoration: none;">👉 צפה בגרף ב-Finviz</a>
#                 </div>
#             </div>
#             """

#         html_body += "</div>"

#         try:
#             print(f"📧 Sending rich report via Resend...")
#             params = {
#                 "from": settings.FROM_EMAIL,
#                 "to": [settings.ALERT_TO_EMAIL],
#                 "subject": subject,
#                 "html": html_body,
#             }
#             resend.Emails.send(params)
#             print(f"✅ Email sent!")
#         except Exception as e:
#             print(f"❌ Resend API Error: {e}")


# import resend
# from app.core.config import settings

# if settings.RESEND_API_KEY:
#     resend.api_key = settings.RESEND_API_KEY

# class EmailService:
#     @staticmethod
#     def format_number(num):
#         """פונקציית עזר להצגת מספרים (1.2B, 500M)"""
#         if not num: return "0"
#         if num > 1_000_000_000:
#             return f"${num/1_000_000_000:.2f}B"
#         if num > 1_000_000:
#             return f"${num/1_000_000:.1f}M"
#         return f"${num:,.0f}"

#     @staticmethod
#     def send_report(opportunities):
#         if not opportunities: return

#         subject = f"🚀 AI Trade Report: {len(opportunities)} Stocks"

#         html_body = """
#         <div dir="rtl" style="font-family: Arial, sans-serif; color: #333; max-width: 700px; margin: 0 auto; background-color: #f4f6f8; padding: 20px;">
#             <h2 style="background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 8px; text-align: center;">
#                 📊 דוח מסחר מבוסס AI
#             </h2>
#         """

#         for opp in opportunities:
#             fin = opp['financials']
#             eff = fin.get('efficiency')
#             raw_rev = fin.get('raw_revenue', {'curr': 0, 'prev': 0})

#             # עיצוב שורת התייעלות
#             if eff:
#                 if eff['is_improving']:
#                     eff_icon = "🟢 משתפר"
#                     eff_bg = "#e8f5e9"
#                 else:
#                     eff_icon = "🔴 נחלש"
#                     eff_bg = "#ffebee"

#                 eff_row = f"""
#                 <tr style="background-color: {eff_bg};">
#                     <td style="padding: 8px;"><b>יחס התייעלות</b> (הוצאות/הכנסות)</td>
#                     <td style="padding: 8px;">{eff['curr_ratio']}%</td>
#                     <td style="padding: 8px;">{eff['prev_ratio']}%</td>
#                     <td style="padding: 8px; font-weight: bold;">{eff_icon}</td>
#                 </tr>
#                 """
#             else:
#                 eff_row = "<tr><td colspan='4'>אין נתונים</td></tr>"

#             html_body += f"""
#             <div style="background-color: white; border-radius: 12px; padding: 25px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">

#                 <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 20px;">
#                     <div>
#                         <h1 style="color:#2c3e50; margin: 0; font-size: 28px;">{opp['ticker']}</h1>
#                         <span style="color: #7f8c8d; font-size: 14px;">{fin.get('industry')}</span>
#                     </div>
#                     <div style="background-color: #27ae60; color: white; padding: 8px 15px; border-radius: 20px; font-weight: bold;">
#                         Score: {int(opp['score'])}
#                     </div>
#                 </div>

#                 <div style="background-color: #f9f9f9; padding: 12px; border-radius: 6px; font-size: 14px; color: #555; margin-bottom: 15px; line-height: 1.5;">
#                     <b>🏢 פרופיל חברה:</b> {opp.get('ai_hebrew_desc', 'לא זמין')}
#                 </div>

#                 <div style="margin-bottom: 20px;">
#                     <h3 style="margin: 0 0 5px 0; color: #d35400; font-size:16px;">📰 טריגר חדשותי:</h3>
#                     <p style="font-size: 15px; font-weight: 500; margin: 0;">{opp['headline']}</p>
#                 </div>

#                 <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; border-right: 4px solid #2196f3; margin-bottom: 20px;">
#                     <b style="color:#1565c0;">🤖 ניתוח אנליסט:</b><br>
#                     {opp.get('ai_analysis', 'לא זמין')}
#                 </div>

#                 <h3 style="font-size:16px; border-bottom: 1px solid #eee; padding-bottom: 5px;">📈 דוח רבעוני (במיליונים)</h3>
#                 <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; text-align: right;">
#                     <tr style="background-color: #f1f1f1;">
#                         <th style="padding: 8px;">מדד</th>
#                         <th style="padding: 8px;">נוכחי</th>
#                         <th style="padding: 8px;">קודם</th>
#                         <th style="padding: 8px;">שינוי (%)</th>
#                     </tr>
#                     <tr>
#                         <td style="padding: 8px; border-bottom: 1px solid #eee;"><b>הכנסות</b> (Revenue)</td>
#                         <td style="padding: 8px; border-bottom: 1px solid #eee;">{EmailService.format_number(raw_rev['curr'])}</td>
#                         <td style="padding: 8px; border-bottom: 1px solid #eee;">{EmailService.format_number(raw_rev['prev'])}</td>
#                         <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; color: {'green' if fin['revenue_growth_qoq'] > 0 else 'red'};">
#                             {fin['revenue_growth_qoq']}%
#                         </td>
#                     </tr>
#                     {eff_row}
#                 </table>

#                 <div style="text-align: center; margin-top: 20px;">
#                     <a href="https://finviz.com/quote.ashx?t={opp['ticker']}" style="color: #3498db; text-decoration: none;">👉 צפה בגרף</a>
#                 </div>
#             </div>
#             """

#         html_body += "</div>"

#         try:
#             params = {
#                 "from": settings.FROM_EMAIL,
#                 "to": [settings.ALERT_TO_EMAIL],
#                 "subject": subject,
#                 "html": html_body,
#             }
#             resend.Emails.send(params)
#             print(f"✅ Email sent successfully!")
#         except Exception as e:
#             print(f"❌ Resend Error: {e}")


# import resend
# from app.core.config import settings

# # הגדרת מפתח API
# if settings.RESEND_API_KEY:
#     resend.api_key = settings.RESEND_API_KEY

# class EmailService:
#     @staticmethod
#     def format_number(num):
#         """פונקציית עזר להצגת מספרים (1.2B, 500M)"""
#         if not num: return "0"
#         if num > 1_000_000_000:
#             return f"${num/1_000_000_000:.2f}B"
#         if num > 1_000_000:
#             return f"${num/1_000_000:.1f}M"
#         return f"${num:,.0f}"

#     @staticmethod
#     def send_report(opportunities):
#         if not opportunities: return

#         # בדיקה שיש מפתחות לפני שליחה
#         if not settings.RESEND_API_KEY or not settings.ALERT_TO_EMAIL:
#             print("❌ Email Error: Missing RESEND_API_KEY or ALERT_TO_EMAIL.")
#             return

#         subject = f"🚀 AI Trade Report: {len(opportunities)} Stocks Found"

#         html_body = """
#         <div dir="rtl" style="font-family: 'Segoe UI', Arial, sans-serif; color: #333; max-width: 700px; margin: 0 auto; background-color: #f4f6f8; padding: 20px;">
#             <h2 style="background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 8px; text-align: center;">
#                 📊 דוח מסחר מבוסס AI
#             </h2>
#         """

#         for opp in opportunities:
#             fin = opp['financials']
#             eff = fin.get('efficiency')
#             raw_rev = fin.get('raw_revenue', {'curr': 0, 'prev': 0})

#             # --- לוגיקה לעיצוב שורת התייעלות ---
#             if eff:
#                 if eff['is_improving']:
#                     eff_icon = "🟢 משתפר"
#                     eff_bg = "#e8f5e9" # ירוק בהיר
#                 else:
#                     eff_icon = "🔴 נחלש"
#                     eff_bg = "#ffebee" # אדום בהיר

#                 eff_row = f"""
#                 <tr style="background-color: {eff_bg};">
#                     <td style="padding: 8px;"><b>יחס התייעלות</b> (הוצאות/הכנסות)</td>
#                     <td style="padding: 8px;">{eff['curr_ratio']}%</td>
#                     <td style="padding: 8px;">{eff['prev_ratio']}%</td>
#                     <td style="padding: 8px; font-weight: bold;">{eff_icon}</td>
#                 </tr>
#                 """
#             else:
#                 eff_row = "<tr><td colspan='4' style='padding:8px;'>אין נתונים מספיקים</td></tr>"

#             html_body += f"""
#             <div style="background-color: white; border-radius: 12px; padding: 25px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">

#                 <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 20px;">
#                     <div>
#                         <h1 style="color:#2c3e50; margin: 0; font-size: 28px;">{opp['ticker']}</h1>
#                         <span style="color: #7f8c8d; font-size: 14px;">{fin.get('industry')}</span>
#                     </div>
#                     <div style="background-color: #27ae60; color: white; padding: 8px 15px; border-radius: 20px; font-weight: bold;">
#                         Score: {int(opp['score'])}
#                     </div>
#                 </div>

#                 <div style="background-color: #f9f9f9; padding: 12px; border-radius: 6px; font-size: 14px; color: #555; margin-bottom: 15px; line-height: 1.5;">
#                     <b>🏢 פרופיל חברה:</b> {opp.get('ai_hebrew_desc', 'לא זמין')}
#                 </div>

#                 <div style="margin-bottom: 20px;">
#                     <h3 style="margin: 0 0 5px 0; color: #d35400; font-size:16px;">📰 טריגר חדשותי:</h3>
#                     <p style="font-size: 15px; font-weight: 500; margin: 0;">{opp['headline']}</p>
#                 </div>

#                 <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; border-right: 4px solid #2196f3; margin-bottom: 20px;">
#                     <b style="color:#1565c0;">🤖 ניתוח אנליסט:</b><br>
#                     {opp.get('ai_analysis', 'לא זמין')}
#                 </div>

#                 <h3 style="font-size:16px; border-bottom: 1px solid #eee; padding-bottom: 5px;">📈 דוח רבעוני (במיליונים)</h3>
#                 <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; text-align: right;">
#                     <tr style="background-color: #f1f1f1;">
#                         <th style="padding: 8px;">מדד</th>
#                         <th style="padding: 8px;">נוכחי</th>
#                         <th style="padding: 8px;">קודם</th>
#                         <th style="padding: 8px;">שינוי (%)</th>
#                     </tr>
#                     <tr>
#                         <td style="padding: 8px; border-bottom: 1px solid #eee;"><b>הכנסות</b> (Revenue)</td>
#                         <td style="padding: 8px; border-bottom: 1px solid #eee;">{EmailService.format_number(raw_rev['curr'])}</td>
#                         <td style="padding: 8px; border-bottom: 1px solid #eee;">{EmailService.format_number(raw_rev['prev'])}</td>
#                         <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; color: {'green' if fin['revenue_growth_qoq'] > 0 else 'red'};">
#                             {fin['revenue_growth_qoq']}%
#                         </td>
#                     </tr>
#                     {eff_row}
#                 </table>

#                 <div style="display: flex; justify-content: space-around; margin-top: 25px; text-align: center; background-color: #fff8e1; padding: 15px; border-radius: 8px; border: 1px solid #ffe0b2;">
#                     <div>
#                         <div style="font-size: 12px; color: #555;">מחיר כניסה</div>
#                         <div style="font-size: 20px; font-weight: bold;">${opp['price']}</div>
#                     </div>
#                     <div>
#                         <div style="font-size: 12px; color: #2e7d32;">יעד (TP)</div>
#                         <div style="font-size: 20px; font-weight: bold; color: #2e7d32;">${fin['target_price']}</div>
#                     </div>
#                     <div>
#                         <div style="font-size: 12px; color: #c62828;">סטופ (SL)</div>
#                         <div style="font-size: 20px; font-weight: bold; color: #c62828;">${fin['stop_loss']}</div>
#                     </div>
#                 </div>

#                 <div style="text-align: center; margin-top: 20px;">
#                     <a href="https://finviz.com/quote.ashx?t={opp['ticker']}" style="background-color: #34495e; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 14px; font-weight: bold;">👉 צפה בגרף המלא</a>
#                 </div>
#             </div>
#             """

#         html_body += "</div>"

#         try:
#             params = {
#                 "from": settings.FROM_EMAIL,
#                 "to": [settings.ALERT_TO_EMAIL],
#                 "subject": subject,
#                 "html": html_body,
#             }
#             resend.Emails.send(params)
#             print(f"✅ Email sent successfully via Resend!")
#         except Exception as e:
#             print(f"❌ Resend API Error: {e}")


# import resend
# from app.core.config import settings

# if settings.RESEND_API_KEY:
#     resend.api_key = settings.RESEND_API_KEY

# class EmailService:
#     @staticmethod
#     def format_number(num):
#         if not num: return "0"
#         if num > 1_000_000_000: return f"${num/1_000_000_000:.2f}B"
#         if num > 1_000_000: return f"${num/1_000_000:.1f}M"
#         return f"${num:,.0f}"

#     @staticmethod
#     # שים לב: הוספנו פרמטר חדש general_news
#     def send_report(stock_opportunities, general_news):
#         if not stock_opportunities and not general_news:
#             return

#         if not settings.RESEND_API_KEY:
#             print("❌ Email Error: Missing RESEND_API_KEY.")
#             return

#         subject = f"🚀 Daily Report: {len(stock_opportunities)} Stocks & {len(general_news)} Headlines"

#         html_body = """
#         <div dir="rtl" style="font-family: 'Segoe UI', Arial, sans-serif; color: #333; max-width: 700px; margin: 0 auto; background-color: #f4f6f8; padding: 20px;">
#             <h2 style="background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 8px; text-align: center;">
#                 📊 דוח מסחר היברידי (AI + News)
#             </h2>
#         """

#         # --- חלק 1: ניתוח מניות עומק (החלק הקיים) ---
#         if stock_opportunities:
#             html_body += "<h2 style='color:#2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom:10px;'>🎯 הזדמנויות מסחר (Swing)</h2>"

#             for opp in stock_opportunities:
#                 fin = opp['financials']
#                 eff = fin.get('efficiency')
#                 raw_rev = fin.get('raw_revenue', {'curr': 0, 'prev': 0})

#                 # עיצוב התייעלות
#                 if eff and eff['is_improving']:
#                     eff_icon = "🟢"
#                     eff_bg = "#e8f5e9"
#                 else:
#                     eff_icon = "🔴"
#                     eff_bg = "#ffebee"
#                 eff_row = f"<tr style='background-color:{eff_bg}'><td><b>התייעלות</b></td><td>{eff['curr_ratio'] if eff else 0}%</td><td>{eff_icon}</td></tr>" if eff else ""

#                 html_body += f"""
#                 <div style="background-color: white; border-radius: 12px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
#                     <div style="display: flex; justify-content: space-between; align-items: center;">
#                         <h2 style="margin:0; color:#2980b9;">{opp['ticker']} <span style="font-size:14px; color:#777;">Score: {int(opp['score'])}</span></h2>
#                     </div>
#                     <p style="font-size:13px; color:#555;"><b>🏢 פרופיל:</b> {opp.get('ai_hebrew_desc', 'N/A')}</p>
#                     <div style="background:#e3f2fd; padding:10px; border-radius:5px; margin:10px 0;">
#                         <b>🤖 AI:</b> {opp.get('ai_analysis', 'N/A')}
#                     </div>
#                     <table style="width:100%; font-size:14px; border-collapse:collapse;">
#                         <tr style="background:#f9f9f9;"><th style="text-align:right;">מדד</th><th style="text-align:right;">נתון</th><th style="text-align:right;">שינוי</th></tr>
#                         <tr><td><b>הכנסות</b></td><td>{EmailService.format_number(raw_rev['curr'])}</td><td style="color:{'green' if fin['revenue_growth_qoq']>0 else 'red'}"><b>{fin['revenue_growth_qoq']}%</b></td></tr>
#                         {eff_row}
#                     </table>
#                     <div style="margin-top:15px; text-align:center; font-weight:bold;">
#                         כניסה: ${opp['price']} | <span style="color:green">יעד: ${fin['target_price']}</span> | <span style="color:red">סטופ: ${fin['stop_loss']}</span>
#                     </div>
#                 </div>
#                 """

#         # --- חלק 2: פיד חדשות גלובלי (החלק החדש) ---
#         if general_news:
#             html_body += """
#             <h2 style="color:#d35400; border-bottom: 2px solid #d35400; padding-bottom:10px; margin-top:40px;">
#                 🌍 חדשות חמות מהיממה האחרונה
#             </h2>
#             <div style="background-color: white; border-radius: 12px; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
#             <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
#             """

#             for news in general_news:
#                 # זיהוי מילות מפתח כדי להדגיש בצבע
#                 hl = news['headline']
#                 color = "#333"
#                 if "FDA" in hl or "Approval" in hl: color = "#2e7d32" # ירוק ל-FDA
#                 elif "Merger" in hl or "Acquisition" in hl: color = "#c2185b" # סגול לעסקאות

#                 html_body += f"""
#                 <tr style="border-bottom: 1px solid #eee;">
#                     <td style="padding: 10px; width: 60px; font-size: 12px; color: #999;">{news['source']}</td>
#                     <td style="padding: 10px;">
#                         <div style="font-weight: bold; color: {color};">{news['headline']}</div>
#                         <div style="font-size: 12px; color: #7f8c8d;">{news['published_at']} | <a href="{news['url']}" style="color:#3498db;">קרא עוד</a></div>
#                     </td>
#                 </tr>
#                 """

#             html_body += "</table></div>"

#         html_body += "</div>"

#         try:
#             params = {
#                 "from": settings.FROM_EMAIL,
#                 "to": [settings.ALERT_TO_EMAIL],
#                 "subject": subject,
#                 "html": html_body,
#             }
#             resend.Emails.send(params)
#             print(f"✅ Email sent successfully via Resend!")
#         except Exception as e:
#             print(f"❌ Resend API Error: {e}")



# import resend
# from app.core.config import settings

# if settings.RESEND_API_KEY:
#     resend.api_key = settings.RESEND_API_KEY

# class EmailService:
#     @staticmethod
#     def format_number(num):
#         if not num: return "0"
#         if num > 1_000_000_000: return f"${num/1_000_000_000:.2f}B"
#         if num > 1_000_000: return f"${num/1_000_000:.1f}M"
#         return f"${num:,.0f}"

#     @staticmethod
#     # שים לב: הוספנו פרמטר חדש general_news
#     def send_report(stock_opportunities, general_news):
#         if not stock_opportunities and not general_news:
#             return

#         if not settings.RESEND_API_KEY:
#             print("❌ Email Error: Missing RESEND_API_KEY.")
#             return

#         subject = f"🚀 Daily Report: {len(stock_opportunities)} Stocks & {len(general_news)} Headlines"

#         html_body = """
#         <div dir="rtl" style="font-family: 'Segoe UI', Arial, sans-serif; color: #333; max-width: 700px; margin: 0 auto; background-color: #f4f6f8; padding: 20px;">
#             <h2 style="background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 8px; text-align: center;">
#                 📊 דוח מסחר היברידי (AI + News)
#             </h2>
#         """

#         # --- חלק 1: ניתוח מניות עומק (החלק הקיים) ---
#         if stock_opportunities:
#             html_body += "<h2 style='color:#2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom:10px;'>🎯 הזדמנויות מסחר (Swing)</h2>"

#             for opp in stock_opportunities:
#                 fin = opp['financials']
#                 eff = fin.get('efficiency')
#                 raw_rev = fin.get('raw_revenue', {'curr': 0, 'prev': 0})

#                 # עיצוב התייעלות
#                 if eff and eff['is_improving']:
#                     eff_icon = "🟢"
#                     eff_bg = "#e8f5e9"
#                 else:
#                     eff_icon = "🔴"
#                     eff_bg = "#ffebee"
#                 eff_row = f"<tr style='background-color:{eff_bg}'><td><b>התייעלות</b></td><td>{eff['curr_ratio'] if eff else 0}%</td><td>{eff_icon}</td></tr>" if eff else ""

#                 html_body += f"""
#                 <div style="background-color: white; border-radius: 12px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
#                     <div style="display: flex; justify-content: space-between; align-items: center;">
#                         <h2 style="margin:0; color:#2980b9;">{opp['ticker']} <span style="font-size:14px; color:#777;">Score: {int(opp['score'])}</span></h2>
#                     </div>
#                     <p style="font-size:13px; color:#555;"><b>🏢 פרופיל:</b> {opp.get('ai_hebrew_desc', 'N/A')}</p>
#                     <div style="background:#e3f2fd; padding:10px; border-radius:5px; margin:10px 0;">
#                         <b>🤖 AI:</b> {opp.get('ai_analysis', 'N/A')}
#                     </div>
#                     <table style="width:100%; font-size:14px; border-collapse:collapse;">
#                         <tr style="background:#f9f9f9;"><th style="text-align:right;">מדד</th><th style="text-align:right;">נתון</th><th style="text-align:right;">שינוי</th></tr>
#                         <tr><td><b>הכנסות</b></td><td>{EmailService.format_number(raw_rev['curr'])}</td><td style="color:{'green' if fin['revenue_growth_qoq']>0 else 'red'}"><b>{fin['revenue_growth_qoq']}%</b></td></tr>
#                         {eff_row}
#                     </table>
#                     <div style="margin-top:15px; text-align:center; font-weight:bold;">
#                         כניסה: ${opp['price']} | <span style="color:green">יעד: ${fin['target_price']}</span> | <span style="color:red">סטופ: ${fin['stop_loss']}</span>
#                     </div>
#                 </div>
#                 """

#         # --- חלק 2: פיד חדשות גלובלי (החלק החדש) ---
#         if general_news:
#             html_body += """
#             <h2 style="color:#d35400; border-bottom: 2px solid #d35400; padding-bottom:10px; margin-top:40px;">
#                 🌍 חדשות חמות מהיממה האחרונה
#             </h2>
#             <div style="background-color: white; border-radius: 12px; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
#             <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
#             """

#             for news in general_news:
#                 # זיהוי מילות מפתח כדי להדגיש בצבע
#                 hl = news['headline']
#                 color = "#333"
#                 if "FDA" in hl or "Approval" in hl: color = "#2e7d32" # ירוק ל-FDA
#                 elif "Merger" in hl or "Acquisition" in hl: color = "#c2185b" # סגול לעסקאות

#                 html_body += f"""
#                 <tr style="border-bottom: 1px solid #eee;">
#                     <td style="padding: 10px; width: 60px; font-size: 12px; color: #999;">{news['source']}</td>
#                     <td style="padding: 10px;">
#                         <div style="font-weight: bold; color: {color};">{news['headline']}</div>
#                         <div style="font-size: 12px; color: #7f8c8d;">{news['published_at']} | <a href="{news['url']}" style="color:#3498db;">קרא עוד</a></div>
#                     </td>
#                 </tr>
#                 """

#             html_body += "</table></div>"

#         html_body += "</div>"

#         try:
#             params = {
#                 "from": settings.FROM_EMAIL,
#                 "to": [settings.ALERT_TO_EMAIL],
#                 "subject": subject,
#                 "html": html_body,
#             }
#             resend.Emails.send(params)
#             print(f"✅ Email sent successfully via Resend!")
#         except Exception as e:
#             print(f"❌ Resend API Error: {e}")


# import resend
# from app.core.config import settings

# if settings.RESEND_API_KEY:
#     resend.api_key = settings.RESEND_API_KEY

# class EmailService:
#     @staticmethod
#     def format_number(num):
#         if not num: return "0"
#         if abs(num) > 1_000_000_000: return f"${num/1_000_000_000:.2f}B"
#         if abs(num) > 1_000_000: return f"${num/1_000_000:.1f}M"
#         return f"${num:,.0f}"

#     @staticmethod
#     def send_report(stock_opportunities, general_news):
#         if not stock_opportunities and not general_news: return
#         if not settings.RESEND_API_KEY: return

#         subject = f"🚀 דוח מסחר: {len(stock_opportunities)} מניות ו-{len(general_news)} חדשות"

#         html_body = """
#         <div dir="rtl" style="font-family: 'Segoe UI', Arial, sans-serif; color: #333; max-width: 750px; margin: 0 auto; background-color: #f4f6f8; padding: 20px;">
#             <h2 style="background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 8px; text-align: center;">
#                 📊 דוח מסחר מקיף (AI + Financials)
#             </h2>
#         """

#         if stock_opportunities:
#             for opp in stock_opportunities:
#                 fin = opp['financials']
#                 rev = fin['revenue']
#                 ni = fin['net_income']
#                 eff = fin['efficiency']

#                 # בתוך הלולאה במייל:
#                 tech_signal = opp['financials'].get('technical_signal', '')
#                 trend_status = opp['financials'].get('trend_status', '')

#                 # צבעים
#                 signal_color = "#d35400" if "פריצת" in tech_signal else "#7f8c8d"
#                 trend_color = "#2e7d32" if "SMA150" in trend_status else "#c62828"

#                 # הוסף את הבלוק הזה מתחת לציון Score:
#                 html_body += f"""
#                 <div style="display:flex; gap:10px; justify-content:center; margin: 10px 0;">
#                     <span style="background-color:{signal_color}; color:white; padding:4px 10px; border-radius:4px; font-size:12px; font-weight:bold;">
#                         {tech_signal}
#                     </span>
#                     <span style="background-color:{trend_color}; color:white; padding:4px 10px; border-radius:4px; font-size:12px; font-weight:bold;">
#                         {trend_status}
#                     </span>
#                 </div>
#                 """

#                 # לוגיקה להתייעלות (נמוך יותר = טוב יותר)
#                 curr_eff = eff['curr'] if eff['curr'] is not None else "N/A"
#                 prev_eff = eff['prev'] if eff['prev'] is not None else "N/A"

#                 eff_display = "-"
#                 eff_bg_color = "" # ברירת מחדל

#                 if isinstance(curr_eff, (int, float)) and isinstance(prev_eff, (int, float)):
#                     # פורמט עם אחוזים
#                     curr_eff_str = f"{curr_eff}%"
#                     prev_eff_str = f"{prev_eff}%"

#                     if curr_eff < prev_eff:
#                         eff_display = "<span style='color:green; font-weight:bold;'>שיפור (התייעלות)</span>"
#                         eff_bg_color = "background-color: #e8f5e9;" # ירוק בהיר
#                     elif curr_eff > prev_eff:
#                         eff_display = "<span style='color:red;'>הרעה (עלייה בהוצאות)</span>"
#                         eff_bg_color = "background-color: #ffebee;" # אדום בהיר
#                 else:
#                     curr_eff_str = curr_eff
#                     prev_eff_str = prev_eff

#                 html_body += f"""
#                 <div style="background-color: white; border-radius: 12px; padding: 25px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">

#                     <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 15px;">
#                         <div>
#                             <h1 style="color:#2c3e50; margin: 0; font-size: 26px;">{opp['ticker']}</h1>
#                             <span style="color: #7f8c8d; font-size: 14px;">שווי שוק: {EmailService.format_number(fin['market_cap'])}</span>
#                         </div>
#                         <div style="background-color: #27ae60; color: white; padding: 5px 15px; border-radius: 15px; font-weight: bold;">
#                             Score: {int(opp['score'])}
#                         </div>
#                     </div>

#                     <div style="background-color: #f9f9f9; padding: 12px; border-radius: 6px; font-size: 14px; color: #555; margin-bottom: 15px; line-height: 1.5;">
#                         <b>🏢 פרופיל חברה:</b> {opp.get('ai_hebrew_desc', 'לא זמין')}
#                     </div>

#                     <div style="margin-bottom: 20px;">
#                         <h3 style="margin: 0 0 5px 0; color: #d35400; font-size:16px;">📰 האירוע החדשותי:</h3>
#                         <p style="font-size: 15px; font-weight: 500; margin: 0;">{opp['headline']}</p>
#                     </div>

#                     <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-right: 4px solid #2196f3;">
#                         <b style="color:#1565c0;">💡 היילייטס מהדוח (AI):</b><br>
#                         <div style="margin-top:5px; line-height:1.5;">{opp.get('ai_analysis', 'עיבוד נתונים...')}</div>
#                     </div>

#                     <h3 style="font-size:16px; border-bottom: 1px solid #eee;">📈 השוואה רבעונית (QoQ)</h3>
#                     <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; text-align: right;">
#                         <tr style="background-color: #f1f1f1;">
#                             <th style="padding: 8px;">מדד</th>
#                             <th style="padding: 8px;">רבעון נוכחי</th>
#                             <th style="padding: 8px;">רבעון קודם</th>
#                             <th style="padding: 8px;">שינוי / מגמה</th>
#                         </tr>
#                         <tr style="border-bottom: 1px solid #eee;">
#                             <td style="padding: 8px;"><b>הכנסות</b> (Revenue)</td>
#                             <td style="padding: 8px;">{EmailService.format_number(rev['curr'])}</td>
#                             <td style="padding: 8px;">{EmailService.format_number(rev['prev'])}</td>
#                             <td style="padding: 8px; font-weight: bold; color: {'green' if rev['change'] > 0 else 'red'};">{rev['change']}%</td>
#                         </tr>
#                         <tr style="border-bottom: 1px solid #eee;">
#                             <td style="padding: 8px;"><b>רווח נקי</b> (Net Income)</td>
#                             <td style="padding: 8px;">{EmailService.format_number(ni['curr'])}</td>
#                             <td style="padding: 8px;">{EmailService.format_number(ni['prev'])}</td>
#                             <td style="padding: 8px; font-weight: bold; color: {'green' if ni['change'] > 0 else 'red'};">{ni['change']}%</td>
#                         </tr>

#                         <tr style="border-bottom: 1px solid #eee; {eff_bg_color}">
#                             <td style="padding: 8px;">
#                                 <b>יחס הוצאות/הכנסות</b><br>
#                                 <span style="font-size:11px; color:#666;">(נמוך יותר = יעיל יותר)</span>
#                             </td>
#                             <td style="padding: 8px; font-weight:bold;">{curr_eff_str}</td>
#                             <td style="padding: 8px;">{prev_eff_str}</td>
#                             <td style="padding: 8px;">{eff_display}</td>
#                         </tr>
#                     </table>

#                     <div style="display: flex; justify-content: space-around; margin-top: 20px; text-align: center; background-color: #fff8e1; padding: 10px; border-radius: 8px;">
#                         <div><span style="color:#555; font-size:12px;">מחיר כניסה</span><br><b>${opp['price']}</b></div>
#                         <div><span style="color:green; font-size:12px;">יעד (TP)</span><br><b style="color:green">${fin['target_price']}</b></div>
#                         <div><span style="color:red; font-size:12px;">סטופ (SL)</span><br><b style="color:red">${fin['stop_loss']}</b></div>
#                     </div>
#                 </div>
#                 """

#         if general_news:
#              html_body += """
#             <h2 style="color:#d35400; border-bottom: 2px solid #d35400; padding-bottom:10px; margin-top:40px;">
#                 🌍 כותרות חמות מהשוק (RSS)
#             </h2>
#             <div style="background-color: white; border-radius: 12px; padding: 10px;">
#             <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
#             """
#              for news in general_news:
#                 html_body += f"""
#                 <tr style="border-bottom: 1px solid #eee;">
#                     <td style="padding: 10px;"><b>{news['headline']}</b><br>
#                     <span style="font-size:12px; color:#888;">{news['source']} | <a href="{news['url']}">קרא עוד</a></span></td>
#                 </tr>"""
#              html_body += "</table></div>"

#         html_body += "</div>"

#         try:
#             resend.Emails.send({
#                 "from": settings.FROM_EMAIL,
#                 "to": [settings.ALERT_TO_EMAIL],
#                 "subject": subject,
#                 "html": html_body
#             })
#             print(f"✅ Email sent successfully!")
#         except Exception as e:
#             print(f"❌ Resend Error: {e}")



# import resend
# from app.core.config import settings

# if settings.RESEND_API_KEY:
#     resend.api_key = settings.RESEND_API_KEY

# class EmailService:
#     @staticmethod
#     def format_number(num):
#         """פונקציית עזר להצגת מספרים (1.2B, 500M)"""
#         if not num: return "0"
#         if abs(num) > 1_000_000_000:
#             return f"${num/1_000_000_000:.2f}B"
#         if abs(num) > 1_000_000:
#             return f"${num/1_000_000:.1f}M"
#         return f"${num:,.0f}"

#     @staticmethod
#     def send_report(stock_opportunities, general_news):
#         if not stock_opportunities and not general_news: return
#         if not settings.RESEND_API_KEY: return

#         subject = f"🚀 דוח מסחר: {len(stock_opportunities)} מניות ו-{len(general_news)} חדשות"

#         html_body = """
#         <div dir="rtl" style="font-family: 'Segoe UI', Arial, sans-serif; color: #333; max-width: 750px; margin: 0 auto; background-color: #f4f6f8; padding: 20px;">
#             <h2 style="background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 8px; text-align: center;">
#                 📊 דוח מסחר מקיף (AI + Technicals)
#             </h2>
#         """

#         # --- חלק המניות ---
#         if stock_opportunities:
#             for opp in stock_opportunities:
#                 fin = opp['financials']
#                 rev = fin['revenue']
#                 ni = fin['net_income']
#                 eff = fin['efficiency']

#                 # חילוץ נתונים טכניים
#                 tech_signal = fin.get('technical_signal', 'ללא איתות')
#                 trend_status = fin.get('trend_status', 'ללא מידע')

#                 # --- השינוי כאן: לוגיקת צבעים מתקדמת ---
#                 if "חציית SMA150" in tech_signal:
#                     signal_bg = "#8e44ad" # סגול יוקרתי (יהלום)
#                 elif "פריצת" in tech_signal or "מומנטום" in tech_signal:
#                     signal_bg = "#d35400" # כתום (פריצה רגילה)
#                 else:
#                     signal_bg = "#95a5a6" # אפור (רגיל)

#                 # צבע למגמה
#                 trend_bg = "#27ae60" if "SMA150" in trend_status else "#c0392b"

#                 # --- לוגיקה להתייעלות ---
#                 curr_eff = eff['curr'] if eff['curr'] is not None else "N/A"
#                 prev_eff = eff['prev'] if eff['prev'] is not None else "N/A"

#                 eff_display = "-"
#                 eff_bg_color = ""

#                 if isinstance(curr_eff, (int, float)) and isinstance(prev_eff, (int, float)):
#                     curr_eff_str = f"{curr_eff}%"
#                     prev_eff_str = f"{prev_eff}%"

#                     if curr_eff < prev_eff:
#                         eff_display = "<span style='color:green; font-weight:bold;'>שיפור (התייעלות)</span>"
#                         eff_bg_color = "background-color: #e8f5e9;"
#                     elif curr_eff > prev_eff:
#                         eff_display = "<span style='color:red;'>הרעה (עלייה בהוצאות)</span>"
#                         eff_bg_color = "background-color: #ffebee;"
#                 else:
#                     curr_eff_str = str(curr_eff)
#                     prev_eff_str = str(prev_eff)

#                 html_body += f"""
#                 <div style="background-color: white; border-radius: 12px; padding: 25px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">

#                     <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 10px;">
#                         <div>
#                             <h1 style="color:#2c3e50; margin: 0; font-size: 26px;">{opp['ticker']}</h1>
#                             <span style="color: #7f8c8d; font-size: 14px;">שווי שוק: {EmailService.format_number(fin['market_cap'])}</span>
#                         </div>
#                         <div style="background-color: #27ae60; color: white; padding: 5px 15px; border-radius: 15px; font-weight: bold;">
#                             Score: {int(opp['score'])}
#                         </div>
#                     </div>

#                     <div style="display:flex; gap:10px; margin-bottom: 20px; font-size:12px;">
#                         <span style="background-color:{signal_bg}; color:white; padding:4px 10px; border-radius:4px; font-weight:bold;">
#                             {tech_signal}
#                         </span>
#                         <span style="background-color:{trend_bg}; color:white; padding:4px 10px; border-radius:4px; font-weight:bold;">
#                             {trend_status}
#                         </span>
#                     </div>

#                     <div style="background-color: #f9f9f9; padding: 12px; border-radius: 6px; font-size: 14px; color: #555; margin-bottom: 15px; line-height: 1.5;">
#                         <b>🏢 פרופיל חברה:</b> {opp.get('ai_hebrew_desc', 'לא זמין')}
#                     </div>

#                     <div style="margin-bottom: 20px;">
#                         <h3 style="margin: 0 0 5px 0; color: #d35400; font-size:16px;">📰 האירוע החדשותי:</h3>
#                         <p style="font-size: 15px; font-weight: 500; margin: 0;">{opp['headline']}</p>
#                     </div>

#                     <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-right: 4px solid #2196f3;">
#                         <b style="color:#1565c0;">💡 ניתוח אנליסט (AI Highlights):</b><br>
#                         <div style="margin-top:5px; line-height:1.5;">{opp.get('ai_analysis', 'עיבוד נתונים...')}</div>
#                     </div>

#                     <h3 style="font-size:16px; border-bottom: 1px solid #eee;">📈 השוואה רבעונית (QoQ)</h3>
#                     <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; text-align: right;">
#                         <tr style="background-color: #f1f1f1;">
#                             <th style="padding: 8px;">מדד</th>
#                             <th style="padding: 8px;">רבעון נוכחי</th>
#                             <th style="padding: 8px;">רבעון קודם</th>
#                             <th style="padding: 8px;">שינוי / מגמה</th>
#                         </tr>
#                         <tr style="border-bottom: 1px solid #eee;">
#                             <td style="padding: 8px;"><b>הכנסות</b> (Revenue)</td>
#                             <td style="padding: 8px;">{EmailService.format_number(rev['curr'])}</td>
#                             <td style="padding: 8px;">{EmailService.format_number(rev['prev'])}</td>
#                             <td style="padding: 8px; font-weight: bold; color: {'green' if rev['change'] > 0 else 'red'};">{rev['change']}%</td>
#                         </tr>
#                         <tr style="border-bottom: 1px solid #eee;">
#                             <td style="padding: 8px;"><b>רווח נקי</b> (Net Income)</td>
#                             <td style="padding: 8px;">{EmailService.format_number(ni['curr'])}</td>
#                             <td style="padding: 8px;">{EmailService.format_number(ni['prev'])}</td>
#                             <td style="padding: 8px; font-weight: bold; color: {'green' if ni['change'] > 0 else 'red'};">{ni['change']}%</td>
#                         </tr>
#                         <tr style="border-bottom: 1px solid #eee; {eff_bg_color}">
#                             <td style="padding: 8px;">
#                                 <b>יחס הוצאות/הכנסות</b><br>
#                                 <span style="font-size:11px; color:#666;">(נמוך יותר = יעיל יותר)</span>
#                             </td>
#                             <td style="padding: 8px; font-weight:bold;">{curr_eff_str}</td>
#                             <td style="padding: 8px;">{prev_eff_str}</td>
#                             <td style="padding: 8px;">{eff_display}</td>
#                         </tr>
#                     </table>

#                     <div style="display: flex; justify-content: space-around; margin-top: 20px; text-align: center; background-color: #fff8e1; padding: 10px; border-radius: 8px;">
#                         <div><span style="color:#555; font-size:12px;">מחיר כניסה</span><br><b>${opp['price']}</b></div>
#                         <div><span style="color:green; font-size:12px;">יעד (TP)</span><br><b style="color:green">${fin['target_price']}</b></div>
#                         <div><span style="color:red; font-size:12px;">סטופ (SL)</span><br><b style="color:red">${fin['stop_loss']}</b></div>
#                     </div>
#                 </div>
#                 """

#         # --- חלק חדשות RSS ---
#         if general_news:
#              html_body += """
#             <h2 style="color:#d35400; border-bottom: 2px solid #d35400; padding-bottom:10px; margin-top:40px;">
#                 🌍 כותרות חמות מהשוק (RSS)
#             </h2>
#             <div style="background-color: white; border-radius: 12px; padding: 10px;">
#             <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
#             """
#              for news in general_news:
#                 html_body += f"""
#                 <tr style="border-bottom: 1px solid #eee;">
#                     <td style="padding: 10px;"><b>{news['headline']}</b><br>
#                     <span style="font-size:12px; color:#888;">{news['source']} | <a href="{news['url']}">קרא עוד</a></span></td>
#                 </tr>"""
#              html_body += "</table></div>"

#         html_body += "</div>"

#         try:
#             resend.Emails.send({
#                 "from": settings.FROM_EMAIL,
#                 "to": [settings.ALERT_TO_EMAIL],
#                 "subject": subject,
#                 "html": html_body
#             })
#             print(f"✅ Email sent successfully!")
#         except Exception as e:
#             print(f"❌ Resend Error: {e}")


# import resend
# from app.core.config import settings

# if settings.RESEND_API_KEY:
#     resend.api_key = settings.RESEND_API_KEY

# class EmailService:
#     @staticmethod
#     def format_number(num):
#         """פונקציית עזר להצגת מספרים (1.2B, 500M)"""
#         if not num: return "0"
#         if abs(num) > 1_000_000_000:
#             return f"${num/1_000_000_000:.2f}B"
#         if abs(num) > 1_000_000:
#             return f"${num/1_000_000:.1f}M"
#         return f"${num:,.0f}"

#     @staticmethod
#     def send_report(stock_opportunities, general_news):
#         if not stock_opportunities and not general_news: return
#         if not settings.RESEND_API_KEY: return

#         subject = f"🚀 דוח מסחר: {len(stock_opportunities)} מניות ו-{len(general_news)} חדשות"

#         html_body = """
#         <div dir="rtl" style="font-family: 'Segoe UI', Arial, sans-serif; color: #333; max-width: 750px; margin: 0 auto; background-color: #f4f6f8; padding: 20px;">
#             <h2 style="background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 8px; text-align: center;">
#                 📊 דוח מסחר מקיף (Hybrid Scan)
#             </h2>
#         """

#         # --- חלק המניות ---
#         if stock_opportunities:
#             for opp in stock_opportunities:
#                 fin = opp['financials']
#                 rev = fin['revenue']
#                 ni = fin['net_income']
#                 eff = fin['efficiency']

#                 # --- התיקון כאן: הגנה מפני None ---
#                 # אם אין איתות (None), נהפוך אותו לסטרינג ריק כדי שהקוד לא יקרוס
#                 raw_signal = fin.get('technical_signal')
#                 tech_signal = raw_signal if raw_signal else "ללא איתות מיוחד"

#                 raw_trend = fin.get('trend_status')
#                 trend_status = raw_trend if raw_trend else "מגמה לא ברורה"

#                 # לוגיקת צבעים מתקדמת
#                 signal_bg = "#95a5a6" # ברירת מחדל אפורה

#                 if "חציית SMA150" in tech_signal:
#                     signal_bg = "#8e44ad" # סגול יוקרתי (יהלום)
#                 elif "פטיש" in tech_signal or "עוטף" in tech_signal:
#                     signal_bg = "#d35400" # כתום (נרות היפוך)
#                 elif "ספל וידית" in tech_signal:
#                     signal_bg = "#2980b9" # כחול (תבנית)
#                 elif "פריצת" in tech_signal or "מומנטום" in tech_signal:
#                     signal_bg = "#e67e22" # כתום בהיר

#                 # צבע למגמה
#                 trend_bg = "#27ae60" if "SMA150" in trend_status else "#c0392b"

#                 # --- לוגיקה להתייעלות ---
#                 curr_eff = eff['curr'] if eff['curr'] is not None else "N/A"
#                 prev_eff = eff['prev'] if eff['prev'] is not None else "N/A"

#                 eff_display = "-"
#                 eff_bg_color = ""

#                 if isinstance(curr_eff, (int, float)) and isinstance(prev_eff, (int, float)):
#                     curr_eff_str = f"{curr_eff}%"
#                     prev_eff_str = f"{prev_eff}%"

#                     if curr_eff < prev_eff:
#                         eff_display = "<span style='color:green; font-weight:bold;'>שיפור (התייעלות)</span>"
#                         eff_bg_color = "background-color: #e8f5e9;"
#                     elif curr_eff > prev_eff:
#                         eff_display = "<span style='color:red;'>הרעה (עלייה בהוצאות)</span>"
#                         eff_bg_color = "background-color: #ffebee;"
#                 else:
#                     curr_eff_str = str(curr_eff)
#                     prev_eff_str = str(prev_eff)

#                 html_body += f"""
#                 <div style="background-color: white; border-radius: 12px; padding: 25px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">

#                     <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 10px;">
#                         <div>
#                             <h1 style="color:#2c3e50; margin: 0; font-size: 26px;">{opp['ticker']}</h1>
#                             <span style="color: #7f8c8d; font-size: 14px;">שווי שוק: {EmailService.format_number(fin['market_cap'])}</span>
#                         </div>
#                         <div style="background-color: #27ae60; color: white; padding: 5px 15px; border-radius: 15px; font-weight: bold;">
#                             Score: {int(opp['score'])}
#                         </div>
#                     </div>

#                     <div style="display:flex; gap:10px; margin-bottom: 20px; font-size:12px;">
#                         <span style="background-color:{signal_bg}; color:white; padding:4px 10px; border-radius:4px; font-weight:bold;">
#                             {tech_signal}
#                         </span>
#                         <span style="background-color:{trend_bg}; color:white; padding:4px 10px; border-radius:4px; font-weight:bold;">
#                             {trend_status}
#                         </span>
#                     </div>

#                     <div style="background-color: #f9f9f9; padding: 12px; border-radius: 6px; font-size: 14px; color: #555; margin-bottom: 15px; line-height: 1.5;">
#                         <b>🏢 פרופיל חברה:</b> {opp.get('ai_hebrew_desc', 'לא זמין')}
#                     </div>

#                     <div style="margin-bottom: 20px;">
#                         <h3 style="margin: 0 0 5px 0; color: #d35400; font-size:16px;">📰 טריגר (חדשות/טכני):</h3>
#                         <p style="font-size: 15px; font-weight: 500; margin: 0;">{opp['headline']}</p>
#                     </div>

#                     <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-right: 4px solid #2196f3;">
#                         <b style="color:#1565c0;">💡 ניתוח אנליסט (AI):</b><br>
#                         <div style="margin-top:5px; line-height:1.5;">{opp.get('ai_analysis', 'עיבוד נתונים...')}</div>
#                     </div>

#                     <h3 style="font-size:16px; border-bottom: 1px solid #eee;">📈 השוואה רבעונית (QoQ)</h3>
#                     <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; text-align: right;">
#                         <tr style="background-color: #f1f1f1;">
#                             <th style="padding: 8px;">מדד</th>
#                             <th style="padding: 8px;">רבעון נוכחי</th>
#                             <th style="padding: 8px;">רבעון קודם</th>
#                             <th style="padding: 8px;">שינוי / מגמה</th>
#                         </tr>
#                         <tr style="border-bottom: 1px solid #eee;">
#                             <td style="padding: 8px;"><b>הכנסות</b> (Revenue)</td>
#                             <td style="padding: 8px;">{EmailService.format_number(rev['curr'])}</td>
#                             <td style="padding: 8px;">{EmailService.format_number(rev['prev'])}</td>
#                             <td style="padding: 8px; font-weight: bold; color: {'green' if rev['change'] > 0 else 'red'};">{rev['change']}%</td>
#                         </tr>
#                         <tr style="border-bottom: 1px solid #eee;">
#                             <td style="padding: 8px;"><b>רווח נקי</b> (Net Income)</td>
#                             <td style="padding: 8px;">{EmailService.format_number(ni['curr'])}</td>
#                             <td style="padding: 8px;">{EmailService.format_number(ni['prev'])}</td>
#                             <td style="padding: 8px; font-weight: bold; color: {'green' if ni['change'] > 0 else 'red'};">{ni['change']}%</td>
#                         </tr>
#                         <tr style="border-bottom: 1px solid #eee; {eff_bg_color}">
#                             <td style="padding: 8px;">
#                                 <b>יחס הוצאות/הכנסות</b><br>
#                                 <span style="font-size:11px; color:#666;">(נמוך יותר = יעיל יותר)</span>
#                             </td>
#                             <td style="padding: 8px; font-weight:bold;">{curr_eff_str}</td>
#                             <td style="padding: 8px;">{prev_eff_str}</td>
#                             <td style="padding: 8px;">{eff_display}</td>
#                         </tr>
#                     </table>

#                     <div style="display: flex; justify-content: space-around; margin-top: 20px; text-align: center; background-color: #fff8e1; padding: 10px; border-radius: 8px;">
#                         <div><span style="color:#555; font-size:12px;">מחיר כניסה</span><br><b>${opp['price']}</b></div>
#                         <div><span style="color:green; font-size:12px;">יעד (TP)</span><br><b style="color:green">${fin['target_price']}</b></div>
#                         <div><span style="color:red; font-size:12px;">סטופ (SL)</span><br><b style="color:red">${fin['stop_loss']}</b></div>
#                     </div>
#                 </div>
#                 """

#         # --- חלק חדשות RSS ---
#         if general_news:
#              html_body += """
#             <h2 style="color:#d35400; border-bottom: 2px solid #d35400; padding-bottom:10px; margin-top:40px;">
#                 🌍 כותרות חמות מהשוק (RSS)
#             </h2>
#             <div style="background-color: white; border-radius: 12px; padding: 10px;">
#             <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
#             """
#              for news in general_news:
#                 html_body += f"""
#                 <tr style="border-bottom: 1px solid #eee;">
#                     <td style="padding: 10px;"><b>{news['headline']}</b><br>
#                     <span style="font-size:12px; color:#888;">{news['source']} | <a href="{news['url']}">קרא עוד</a></span></td>
#                 </tr>"""
#              html_body += "</table></div>"

#         html_body += "</div>"

#         try:
#             resend.Emails.send({
#                 "from": settings.FROM_EMAIL,
#                 "to": [settings.ALERT_TO_EMAIL],
#                 "subject": subject,
#                 "html": html_body
#             })
#             print(f"✅ Email sent successfully!")
#         except Exception as e:
#             print(f"❌ Resend Error: {e}")


# import resend
# from app.core.config import settings

# if settings.RESEND_API_KEY:
#     resend.api_key = settings.RESEND_API_KEY

# class EmailService:
#     @staticmethod
#     def format_number(num):
#         if not num: return "0"
#         if abs(num) > 1_000_000_000: return f"${num/1_000_000_000:.2f}B"
#         if abs(num) > 1_000_000: return f"${num/1_000_000:.1f}M"
#         return f"${num:,.0f}"

#     @staticmethod
#     def send_report(stock_opportunities, general_news):
#         if not stock_opportunities and not general_news: return
#         if not settings.RESEND_API_KEY: return

#         subject = f"🚀 דוח מסחר: {len(stock_opportunities)} הזדמנויות"

#         html_body = """
#         <div dir="rtl" style="font-family: 'Segoe UI', sans-serif; max-width: 750px; margin: 0 auto; background: #f4f6f8; padding: 20px;">
#             <h2 style="background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 8px; text-align: center;">
#                 📊 דוח מסחר היברידי (AI + SMA150)
#             </h2>
#         """

#         if stock_opportunities:
#             for opp in stock_opportunities:
#                 fin = opp['financials']
#                 rev = fin.get('revenue', {})
#                 ni = fin.get('net_income', {})

#                 tech_signal = fin.get('technical_signal', 'ללא איתות')
#                 trend_status = fin.get('trend_status', 'ללא מידע')
#                 vol_ratio = fin.get('volume_ratio', 1.0)

#                 # צבעים
#                 signal_bg = "#8e44ad" if "SMA150" in str(tech_signal) else ("#d35400" if "פריצת" in str(tech_signal) else "#7f8c8d")
#                 trend_color = "#27ae60" if "מעל SMA150" in trend_status else "#c0392b"

#                 # תצוגת ווליום
#                 vol_text = "ווליום רגיל"
#                 vol_color = "#7f8c8d"
#                 if vol_ratio > 1.5:
#                     vol_text = f"🔥 ווליום גבוה (x{vol_ratio})"
#                     vol_color = "#d35400"
#                 elif vol_ratio > 3.0:
#                     vol_text = f"🚀 ווליום מטורף (x{vol_ratio})"
#                     vol_color = "#c0392b"

#                 html_body += f"""
#                 <div style="background: white; border-radius: 12px; padding: 25px; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">

#                     <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; padding-bottom: 10px;">
#                         <div>
#                             <h1 style="margin: 0; color: #2c3e50;">{opp['ticker']} <span style="font-size:16px; color:#555;">${opp['price']}</span></h1>
#                         </div>
#                         <div style="background: #27ae60; color: white; padding: 5px 12px; border-radius: 20px; font-weight: bold;">
#                             Score: {int(opp['score'])}
#                         </div>
#                     </div>

#                     <div style="display:flex; gap:10px; flex-wrap:wrap; margin: 15px 0;">
#                         <span style="background:{signal_bg}; color:white; padding:4px 10px; border-radius:4px; font-weight:bold; font-size:13px;">
#                             {tech_signal}
#                         </span>
#                         <span style="background:{trend_color}; color:white; padding:4px 10px; border-radius:4px; font-weight:bold; font-size:13px;">
#                             {trend_status}
#                         </span>
#                         <span style="background:{vol_color}; color:white; padding:4px 10px; border-radius:4px; font-weight:bold; font-size:13px;">
#                             {vol_text}
#                         </span>
#                     </div>

#                     <div style="background: #f8f9fa; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; line-height: 1.5;">
#                         <b>🏢 פרופיל חברה:</b> {opp.get('ai_hebrew_desc', 'אין תיאור זמין')}
#                     </div>

#                     <div style="margin-bottom: 15px;">
#                         <b style="color:#d35400;">📰 כותרת:</b> {opp['headline']}
#                     </div>

#                     <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
#                         <b style="color:#1565c0;">💡 ניתוח AI:</b>
#                         <div style="margin-top:5px; font-size:14px;">{opp.get('ai_analysis', '...')}</div>
#                     </div>

#                     <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
#                         <tr style="background: #eee;">
#                             <th style="padding:8px; text-align:right;">נתון</th>
#                             <th style="padding:8px; text-align:right;">נוכחי</th>
#                             <th style="padding:8px; text-align:right;">קודם</th>
#                             <th style="padding:8px; text-align:right;">שינוי</th>
#                         </tr>
#                         <tr style="border-bottom:1px solid #eee;">
#                             <td style="padding:8px;">הכנסות</td>
#                             <td style="padding:8px;">{EmailService.format_number(rev.get('curr', 0))}</td>
#                             <td style="padding:8px;">{EmailService.format_number(rev.get('prev', 0))}</td>
#                             <td style="padding:8px; color:{'green' if rev.get('change',0) > 0 else 'red'}">
#                                 {rev.get('change', 0)}%
#                             </td>
#                         </tr>
#                         <tr>
#                             <td style="padding:8px;">רווח נקי</td>
#                             <td style="padding:8px;">{EmailService.format_number(ni.get('curr', 0))}</td>
#                             <td style="padding:8px;">{EmailService.format_number(ni.get('prev', 0))}</td>
#                             <td style="padding:8px; color:{'green' if ni.get('change',0) > 0 else 'red'}">
#                                 {ni.get('change', 0)}%
#                             </td>
#                         </tr>
#                     </table>
#                 </div>
#                 """

#         # RSS News Part
#         if general_news:
#              html_body += "<h3 style='margin-top:30px; border-bottom:2px solid #ccc;'>חדשות כלליות</h3>"
#              for news in general_news:
#                 html_body += f"<div style='margin-bottom:10px; font-size:13px;'>• <b>{news['headline']}</b> <a href='{news['url']}'>קרא עוד</a></div>"

#         html_body += "</div>"

#         try:
#             resend.Emails.send({
#                 "from": settings.FROM_EMAIL,
#                 "to": [settings.ALERT_TO_EMAIL],
#                 "subject": subject,
#                 "html": html_body
#             })
#             print(f"✅ Email sent!")
#         except Exception as e:
#             print(f"❌ Resend Error: {e}")


import resend
from app.core.config import settings

if settings.RESEND_API_KEY:
    resend.api_key = settings.RESEND_API_KEY

import re as _re


def _md_to_html(text: str) -> str:
    """
    Lightweight markdown → HTML for the AI analyst output.
    Converts ## headers, **bold**, and newlines.
    """
    if not text:
        return ""
    # ## Section headers
    text = _re.sub(
        r"^## (.+)$",
        r'<div style="font-weight:700;color:#0d2b5e;margin:12px 0 4px;font-size:14px;'
        r'border-right:3px solid #0051a5;padding-right:8px;">\1</div>',
        text,
        flags=_re.MULTILINE,
    )
    # **bold**
    text = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # paragraph breaks
    text = text.replace("\n\n", "<br><br>").replace("\n", "<br>")
    return text


class EmailService:
    @staticmethod
    def format_number(num):
        if not num: return "0"
        if abs(num) > 1_000_000_000: return f"${num/1_000_000_000:.2f}B"
        if abs(num) > 1_000_000: return f"${num/1_000_000:.1f}M"
        return f"${num:,.0f}"

    @staticmethod
    def send_report(stock_opportunities, general_news):
        if not stock_opportunities and not general_news:
            return
        if not settings.RESEND_API_KEY:
            return

        n = len(stock_opportunities)
        subject = f"🏦 Equity Research Report: {n} הזדמנויות מוסדיות"

        html_body = (
            '<div dir="rtl" style="font-family:\'Segoe UI\',Arial,sans-serif;'
            "max-width:760px;margin:0 auto;background:#f0f2f5;padding:20px;\">"
            '<div style="background:linear-gradient(135deg,#003087,#0051a5);'
            "color:white;padding:22px 30px;border-radius:10px;margin-bottom:24px;"
            'text-align:center;">'
            '<div style="font-size:11px;letter-spacing:2px;opacity:0.7;margin-bottom:4px;">'
            "EQUITY RESEARCH · INSTITUTIONAL INTELLIGENCE</div>"
            f'<h2 style="margin:0;font-size:22px;font-weight:700;">📊 דוח אנליסט בכיר — {n} הזדמנויות</h2>'
            "</div>"
        )

        for opp in stock_opportunities:
            ticker = opp["ticker"]
            price  = opp.get("price", "N/A")
            score  = int(opp.get("score", 0))
            fin    = opp.get("financials", {})

            rev = fin.get("revenue", {})
            ni  = fin.get("net_income", {})

            tech_signal  = fin.get("technical_signal") or "—"
            trend_status = fin.get("trend_status", "—")
            vol_ratio    = fin.get("volume_ratio", 1.0)

            # Technical badge colours
            signal_bg  = "#6d28d9" if "SMA150" in str(tech_signal) else (
                          "#d97706" if "פריצת" in str(tech_signal) else "#64748b")
            trend_color = "#16a34a" if "מעל SMA150" in trend_status else "#dc2626"

            # Volume badge
            if vol_ratio >= 3.0:
                vol_text, vol_color = f"🚀 ווליום x{vol_ratio}", "#dc2626"
            elif vol_ratio >= 1.5:
                vol_text, vol_color = f"🔥 ווליום x{vol_ratio}", "#d97706"
            else:
                vol_text, vol_color = f"ווליום x{vol_ratio}", "#64748b"

            # XGBoost confidence badge
            conf = opp.get("confidence")
            if conf is not None:
                conf_color = "#16a34a" if conf >= 60 else ("#d97706" if conf >= 40 else "#dc2626")
                conf_badge = (
                    f'<div style="background:{conf_color};color:white;padding:6px 14px;'
                    f'border-radius:20px;font-weight:700;font-size:13px;'
                    f'display:inline-block;margin-left:8px;">'
                    f"ביטחון XGBoost: {conf:.0f}%</div>"
                )
            else:
                conf_badge = ""

            # 5-year margins
            gm = fin.get("gross_margin_5y", [])
            om = fin.get("operating_margin_5y", [])
            nm = fin.get("net_margin_5y", [])
            gm_str = " → ".join(f"{m:.1f}%" for m in gm[:4]) if gm else "N/A"
            om_str = " → ".join(f"{m:.1f}%" for m in om[:4]) if om else "N/A"
            nm_str = " → ".join(f"{m:.1f}%" for m in nm[:4]) if nm else "N/A"

            # Balance sheet
            dte        = fin.get("debt_to_equity", "N/A")
            curr_ratio = fin.get("current_ratio", "N/A")
            cash_str   = EmailService.format_number(fin.get("total_cash", 0))
            debt_str   = EmailService.format_number(fin.get("total_debt", 0))

            # FCF
            fcf_list = fin.get("fcf_history", [])
            fcf_str  = " → ".join(EmailService.format_number(v) for v in fcf_list[:4]) if fcf_list else "N/A"
            fcf_cagr = fin.get("fcf_growth", "N/A")

            # Valuation
            pe  = fin.get("pe_ratio", "N/A")
            peg = fin.get("peg_ratio", "N/A")

            # Revenue / net income QoQ
            rev_c  = rev.get("change", 0)
            ni_c   = ni.get("change", 0)

            # AI analysis with markdown → HTML
            analysis_html = _md_to_html(opp.get("ai_analysis", ""))

            html_body += f"""
<div style="background:white;border-radius:12px;margin-bottom:28px;
     box-shadow:0 4px 15px rgba(0,0,0,0.07);overflow:hidden;
     border:1px solid #e2e8f0;">

  <!-- ── Header bar ── -->
  <div style="background:linear-gradient(90deg,#003087,#0051a5);
              color:white;padding:16px 24px;
              display:flex;justify-content:space-between;align-items:center;">
    <div>
      <div style="font-size:24px;font-weight:700;letter-spacing:1px;">{ticker}</div>
      <div style="font-size:13px;opacity:0.8;margin-top:2px;">${price}</div>
    </div>
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      {conf_badge}
      <div style="background:rgba(255,255,255,0.2);border-radius:20px;
                  padding:6px 14px;font-size:13px;font-weight:700;">
        ציון חדשות: {score}
      </div>
    </div>
  </div>

  <!-- ── Technical signals strip ── -->
  <div style="background:#f8fafc;padding:10px 24px;
              display:flex;gap:8px;flex-wrap:wrap;
              border-bottom:1px solid #e2e8f0;">
    <span style="background:{signal_bg};color:white;padding:4px 10px;
                 border-radius:4px;font-weight:600;font-size:12px;">{tech_signal}</span>
    <span style="background:{trend_color};color:white;padding:4px 10px;
                 border-radius:4px;font-weight:600;font-size:12px;">{trend_status}</span>
    <span style="background:{vol_color};color:white;padding:4px 10px;
                 border-radius:4px;font-weight:600;font-size:12px;">{vol_text}</span>
  </div>

  <!-- ── Body ── -->
  <div style="padding:24px;">

    <!-- Company profile -->
    <div style="background:#f8fafc;padding:12px 16px;border-radius:6px;
                margin-bottom:16px;font-size:14px;line-height:1.5;
                border-right:3px solid #cbd5e1;">
      <b>🏢 פרופיל חברה:</b> {opp.get("ai_hebrew_desc", "—")}
    </div>

    <!-- Catalyst -->
    <div style="margin-bottom:16px;font-size:14px;">
      <b style="color:#b45309;">📰 קטליסט:</b> {opp.get("headline", "—")}
    </div>

    <!-- Goldman Sachs Research Note -->
    <div style="background:#eef2ff;border-right:4px solid #003087;
                padding:16px 20px;border-radius:6px;margin-bottom:20px;">
      <div style="font-size:11px;font-weight:700;color:#003087;
                  text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px;">
        🏦 הערת מחקר — Senior Equity Analyst
      </div>
      <div style="font-size:14px;line-height:1.75;color:#1e293b;">
        {analysis_html}
      </div>
    </div>

    <!-- Financial data table -->
    <div style="font-size:13px;font-weight:600;color:#334155;margin-bottom:8px;">
      📊 נתונים פיננסיים מוסדיים
    </div>
    <table style="width:100%;border-collapse:collapse;font-size:13px;text-align:right;">

      <!-- Margins header -->
      <tr style="background:#dbeafe;">
        <td colspan="4" style="padding:7px 10px;font-weight:700;color:#1d4ed8;">
          מרווחי רווחיות (5 שנים, חדש→ישן)
        </td>
      </tr>
      <tr style="border-bottom:1px solid #e2e8f0;">
        <td style="padding:6px 10px;color:#475569;">גרוס מרג'ין</td>
        <td colspan="3" style="padding:6px 10px;">{gm_str}</td>
      </tr>
      <tr style="background:#f8fafc;border-bottom:1px solid #e2e8f0;">
        <td style="padding:6px 10px;color:#475569;">מרג'ין תפעולי</td>
        <td colspan="3" style="padding:6px 10px;">{om_str}</td>
      </tr>
      <tr style="border-bottom:1px solid #e2e8f0;">
        <td style="padding:6px 10px;color:#475569;">מרג'ין נקי</td>
        <td colspan="3" style="padding:6px 10px;">{nm_str}</td>
      </tr>

      <!-- QoQ quarterly -->
      <tr style="background:#dcfce7;">
        <td colspan="4" style="padding:7px 10px;font-weight:700;color:#15803d;">
          ביצועי רבעון (QoQ)
        </td>
      </tr>
      <tr style="border-bottom:1px solid #e2e8f0;">
        <td style="padding:6px 10px;color:#475569;">הכנסות</td>
        <td style="padding:6px 10px;">{EmailService.format_number(rev.get("curr", 0))}</td>
        <td style="padding:6px 10px;">{EmailService.format_number(rev.get("prev", 0))}</td>
        <td style="padding:6px 10px;color:{'#16a34a' if rev_c > 0 else '#dc2626'};font-weight:600;">
          {rev_c:+.1f}%
        </td>
      </tr>
      <tr style="background:#f8fafc;border-bottom:1px solid #e2e8f0;">
        <td style="padding:6px 10px;color:#475569;">רווח נקי</td>
        <td style="padding:6px 10px;">{EmailService.format_number(ni.get("curr", 0))}</td>
        <td style="padding:6px 10px;">{EmailService.format_number(ni.get("prev", 0))}</td>
        <td style="padding:6px 10px;color:{'#16a34a' if ni_c > 0 else '#dc2626'};font-weight:600;">
          {ni_c:+.1f}%
        </td>
      </tr>

      <!-- Balance sheet + FCF -->
      <tr style="background:#fdf4ff;">
        <td colspan="4" style="padding:7px 10px;font-weight:700;color:#7e22ce;">
          מאזן · FCF · שווי
        </td>
      </tr>
      <tr style="border-bottom:1px solid #e2e8f0;">
        <td style="padding:6px 10px;color:#475569;">חוב/הון (D/E)</td>
        <td style="padding:6px 10px;">{dte}</td>
        <td style="padding:6px 10px;color:#475569;">יחס שוטף</td>
        <td style="padding:6px 10px;">{curr_ratio}</td>
      </tr>
      <tr style="background:#f8fafc;border-bottom:1px solid #e2e8f0;">
        <td style="padding:6px 10px;color:#475569;">מזומן</td>
        <td style="padding:6px 10px;">{cash_str}</td>
        <td style="padding:6px 10px;color:#475569;">חוב כולל</td>
        <td style="padding:6px 10px;">{debt_str}</td>
      </tr>
      <tr style="border-bottom:1px solid #e2e8f0;">
        <td style="padding:6px 10px;color:#475569;">FCF (חדש→ישן)</td>
        <td colspan="3" style="padding:6px 10px;">{fcf_str}</td>
      </tr>
      <tr style="background:#f8fafc;border-bottom:1px solid #e2e8f0;">
        <td style="padding:6px 10px;color:#475569;">FCF CAGR 3 שנים</td>
        <td style="padding:6px 10px;">{fcf_cagr}%</td>
        <td style="padding:6px 10px;color:#475569;">P/E · PEG</td>
        <td style="padding:6px 10px;">{pe} · {peg}</td>
      </tr>

    </table>

  </div><!-- /body -->

  <!-- ── Footer links ── -->
  <div style="background:#f8fafc;padding:12px 24px;border-top:1px solid #e2e8f0;
              display:flex;gap:10px;justify-content:flex-start;flex-wrap:wrap;">
    <a href="https://www.tradingview.com/chart/?symbol={ticker}"
       style="background:#1565c0;color:white;text-decoration:none;
              padding:8px 16px;border-radius:5px;font-size:13px;font-weight:600;">
      📈 גרף TradingView ➜
    </a>
    <a href="https://finviz.com/quote.ashx?t={ticker}"
       style="background:#34495e;color:white;text-decoration:none;
              padding:8px 16px;border-radius:5px;font-size:13px;font-weight:600;">
      🔍 Finviz ➜
    </a>
    <a href="https://stockgrid.io/darkpools/{ticker}"
       style="background:#2c3e50;color:white;text-decoration:none;
              padding:8px 16px;border-radius:5px;font-size:13px;font-weight:600;">
      🌑 Dark Pools ➜
    </a>
  </div>

</div>
"""

        if general_news:
            html_body += (
                "<div style='margin-top:20px;background:white;border-radius:8px;"
                "padding:16px 20px;box-shadow:0 2px 8px rgba(0,0,0,0.05);'>"
                "<h3 style='margin:0 0 12px;font-size:15px;border-bottom:1px solid #eee;padding-bottom:8px;'>"
                "📰 חדשות שוק כלליות</h3>"
            )
            for news in general_news:
                html_body += (
                    f"<div style='margin-bottom:8px;font-size:13px;'>"
                    f"• <b>{news['headline']}</b> "
                    f"<a href='{news['url']}' style='color:#1565c0;'>קרא עוד</a></div>"
                )
            html_body += "</div>"

        html_body += (
            "<div style='text-align:center;margin-top:16px;font-size:11px;color:#94a3b8;'>"
            "Institutional Equity Research · Powered by AI + XGBoost · "
            "Not investment advice</div></div>"
        )

        try:
            resend.Emails.send({
                "from":    settings.FROM_EMAIL,
                "to":      [settings.ALERT_TO_EMAIL],
                "subject": subject,
                "html":    html_body,
            })
            print(f"✅ Institutional research email sent ({n} stocks).")
        except Exception as e:
            print(f"❌ Resend Error: {e}")

    # ------------------------------------------------------------------
    # Options email  (Daily Options Brief)
    # ------------------------------------------------------------------

    @staticmethod
    def send_options_report(report: dict, ai_analysis: dict) -> None:
        """
        Sends the Daily Options Brief email.
        report      : dict from OptionsService.build_report()
        ai_analysis : dict from AIService.get_options_analysis()
        """
        if not settings.RESEND_API_KEY:
            return

        spx      = report.get("spx_price", "N/A")
        vix      = report.get("vix", "N/A")
        dt       = report.get("scan_date", "")
        setup    = report.get("spx_setup") or {}
        stocks   = report.get("stock_options") or []
        spx_ai   = _md_to_html(ai_analysis.get("spx_analysis", ""))
        stock_ai = _md_to_html(ai_analysis.get("stock_analysis", ""))

        vix_color = "#dc2626" if float(vix or 0) > 25 else (
                    "#d97706" if float(vix or 0) > 18 else "#16a34a")

        subject = f"📊 Daily Options Brief — SPX {spx}  |  VIX {vix}"

        # ── Header ──────────────────────────────────────────────────────
        html = (
            '<div dir="rtl" style="font-family:\'Segoe UI\',Arial,sans-serif;'
            'max-width:780px;margin:0 auto;background:#0d1117;padding:20px;">'

            # Title bar
            '<div style="background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);'
            'color:white;padding:24px 30px;border-radius:12px;margin-bottom:20px;text-align:center;">'
            '<div style="font-size:11px;letter-spacing:3px;opacity:0.6;margin-bottom:6px;">'
            'TASTYTRADE · OPTIONS INTELLIGENCE · DAILY BRIEF</div>'
            f'<h2 style="margin:0;font-size:24px;font-weight:700;">📊 Daily Options Brief — {dt}</h2>'
            '<div style="margin-top:12px;display:flex;justify-content:center;gap:24px;flex-wrap:wrap;">'
            f'<div style="background:rgba(255,255,255,0.1);padding:8px 20px;border-radius:20px;">'
            f'<b>SPX</b> {spx}</div>'
            f'<div style="background:{vix_color};padding:8px 20px;border-radius:20px;">'
            f'<b>VIX</b> {vix}</div>'
            '</div></div>'
        )

        # ── 0DTE Trade Ticket ──────────────────────────────────────────
        if setup:
            spy_px   = setup.get("spy_price", "—")
            put_s    = setup.get("put_spread") or {}
            call_s   = setup.get("call_spread") or {}
            tot_cr   = setup.get("total_credit", "—")
            stop     = setup.get("stop_loss", "—")
            tgt      = setup.get("profit_target", "—")
            expiry   = setup.get("expiry", "—")

            def _spread_cell(s: dict, bg: str, emoji: str, title: str) -> str:
                if not s:
                    return (f'<td style="padding:14px;background:{bg};border-radius:8px;">'
                            f'<div style="font-weight:700;color:white;">{emoji} {title}</div>'
                            '<div style="color:rgba(255,255,255,0.6);margin-top:6px;">לא זמין</div></td>')
                return (
                    f'<td style="padding:14px;background:{bg};border-radius:8px;width:50%;">'
                    f'<div style="font-weight:700;font-size:14px;color:white;margin-bottom:8px;">{emoji} {title}</div>'
                    f'<div style="color:rgba(255,255,255,0.9);font-size:13px;line-height:1.8;">'
                    f'Short: <b>{s.get("short_strike")}</b><br>'
                    f'Long: <b>{s.get("long_strike")}</b><br>'
                    f'קרדיט: <b>${s.get("credit")}</b><br>'
                    f'Delta: <b>{s.get("short_delta")}</b><br>'
                    f'Max Loss: <b>${s.get("max_loss")}</b><br>'
                    f'Breakeven: <b>{s.get("breakeven")}</b>'
                    f'</div></td>'
                )

            html += (
                '<div style="background:#111827;border:1px solid #374151;border-radius:12px;'
                'padding:20px;margin-bottom:20px;">'
                '<div style="text-align:center;font-size:13px;font-weight:700;color:#f59e0b;'
                'letter-spacing:2px;margin-bottom:16px;">🎫 0DTE SPX IRON CONDOR TRADE TICKET</div>'

                '<div style="background:#1f2937;border-radius:8px;padding:10px 16px;'
                'display:flex;justify-content:space-between;margin-bottom:14px;'
                'font-size:13px;color:#9ca3af;">'
                f'<span>SPY: <b style="color:white">{spy_px}</b></span>'
                f'<span>Expiry: <b style="color:white">{expiry}</b></span>'
                f'<span>VIX: <b style="color:{vix_color}">{vix}</b></span>'
                '</div>'

                '<table style="width:100%;border-collapse:separate;border-spacing:8px;">'
                '<tr>'
                + _spread_cell(put_s,  "rgba(22,163,74,0.25)",  "🐂", "Bull Put Spread")
                + _spread_cell(call_s, "rgba(220,38,38,0.25)",  "🐻", "Bear Call Spread")
                + '</tr></table>'

                '<div style="background:#1f2937;border-radius:8px;padding:12px 16px;'
                'margin-top:14px;display:flex;justify-content:space-between;flex-wrap:wrap;'
                'gap:8px;font-size:13px;">'
                f'<span style="color:#4ade80;">✅ קרדיט כולל: <b>${tot_cr}</b></span>'
                f'<span style="color:#f59e0b;">🎯 Profit Target: <b>${tgt}</b> (50%)</span>'
                f'<span style="color:#f87171;">🛑 Stop Loss: <b>${stop}</b> (2× קרדיט)</span>'
                '</div>'
            )

            # AI SPX analysis
            if spx_ai:
                html += (
                    '<div style="background:#0f172a;border-right:3px solid #f59e0b;'
                    'padding:14px 16px;margin-top:14px;border-radius:4px;">'
                    '<div style="font-size:11px;color:#f59e0b;font-weight:700;'
                    'letter-spacing:1px;margin-bottom:8px;">🤖 ניתוח Tastytrade Analyst</div>'
                    f'<div style="font-size:13px;line-height:1.8;color:#e2e8f0;">{spx_ai}</div>'
                    '</div>'
                )

            html += '</div>'

        # ── Stock options cards (green = CALL/Bullish, red = PUT/Bearish) ──
        if stocks:
            html += (
                '<div style="margin-bottom:20px;">'
                '<div style="font-size:13px;font-weight:700;color:#e2e8f0;'
                'letter-spacing:2px;margin-bottom:14px;padding:0 4px;">'
                '📈 STOCK OPTIONS — CREDIT SPREADS</div>'
            )

            for opt in stocks:
                is_bull    = opt["direction"] == "Bullish"
                iv_pct     = f"{opt.get('iv', 0) * 100:.0f}%" if opt.get("iv") else "—"
                conf_str   = f"{opt['confidence']:.0f}%" if opt.get("confidence") else "—"
                conf_color = (
                    "#4ade80" if (opt.get("confidence") or 0) >= 60
                    else ("#fbbf24" if (opt.get("confidence") or 0) >= 40 else "#f87171")
                )

                # Direction-specific theming
                if is_bull:
                    border_c   = "#16a34a"
                    hdr_grad   = "linear-gradient(90deg,#14532d,#166534)"
                    accent_c   = "#4ade80"
                    dir_label  = "קניית CALL"
                    dir_emoji  = "📈"
                    badge_bg   = "rgba(74,222,128,0.15)"
                else:
                    border_c   = "#dc2626"
                    hdr_grad   = "linear-gradient(90deg,#7f1d1d,#991b1b)"
                    accent_c   = "#f87171"
                    dir_label  = "קניית PUT"
                    dir_emoji  = "📉"
                    badge_bg   = "rgba(248,113,113,0.15)"

                # News headlines
                news = opt.get("news_headlines") or []
                news_html = ""
                if news:
                    news_items = "".join(
                        f'<div style="padding:3px 0;color:#cbd5e1;font-size:12px;">'
                        f'• {h}</div>'
                        for h in news[:3]
                    )
                    news_html = (
                        f'<div style="background:#0f172a;border-right:2px solid {border_c};'
                        f'padding:10px 14px;margin-top:12px;border-radius:4px;">'
                        f'<div style="font-size:11px;color:{accent_c};font-weight:700;'
                        f'letter-spacing:1px;margin-bottom:6px;">📰 חדשות אחרונות</div>'
                        f'{news_items}</div>'
                    )

                html += (
                    f'<div style="border-radius:12px;overflow:hidden;margin-bottom:16px;'
                    f'border:1px solid {border_c};">'

                    # Card header
                    f'<div style="background:{hdr_grad};padding:14px 18px;'
                    f'display:flex;justify-content:space-between;align-items:center;">'
                    f'<div>'
                    f'<div style="color:white;font-size:22px;font-weight:700;letter-spacing:1px;">'
                    f'{dir_emoji} {opt["ticker"]}</div>'
                    f'<div style="color:rgba(255,255,255,0.8);font-size:14px;margin-top:3px;">'
                    f'{dir_label} — <span style="opacity:0.7">{opt["strategy"]}</span></div>'
                    f'</div>'
                    f'<div style="text-align:left;">'
                    f'<div style="background:rgba(255,255,255,0.2);color:white;'
                    f'padding:6px 14px;border-radius:20px;font-size:13px;font-weight:700;">'
                    f'XGBoost: <span style="color:{conf_color}">{conf_str}</span></div>'
                    f'<div style="color:rgba(255,255,255,0.6);font-size:12px;'
                    f'margin-top:4px;text-align:center;">מחיר: ${opt.get("spot_price","—")}</div>'
                    f'</div></div>'

                    # Card body
                    f'<div style="background:#111827;padding:14px 18px;">'

                    # Strikes / expiry row
                    f'<div style="display:flex;gap:14px;flex-wrap:wrap;'
                    f'margin-bottom:12px;font-size:13px;">'
                    f'<span style="color:#9ca3af;">Short: <b style="color:white">'
                    f'{opt.get("short_strike","—")}</b></span>'
                    f'<span style="color:#9ca3af;">Long: <b style="color:white">'
                    f'{opt.get("long_strike","—")}</b></span>'
                    f'<span style="color:#9ca3af;">פקיעה: <b style="color:white">'
                    f'{opt.get("expiry","—")} ({opt.get("days","—")}d)</b></span>'
                    f'<span style="color:#9ca3af;">Delta: <b style="color:#93c5fd">'
                    f'{opt.get("delta","—")}</b></span>'
                    f'<span style="color:#9ca3af;">IV: <b style="color:#fbbf24">'
                    f'{iv_pct}</b></span>'
                    f'</div>'

                    # P&L badges
                    f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">'
                    f'<span style="background:rgba(74,222,128,0.15);color:#4ade80;'
                    f'padding:5px 12px;border-radius:6px;font-size:12px;font-weight:700;">'
                    f'קרדיט: ${opt.get("credit","—")}</span>'
                    f'<span style="background:rgba(74,222,128,0.12);color:#4ade80;'
                    f'padding:5px 12px;border-radius:6px;font-size:12px;">'
                    f'Max Profit: ${opt.get("max_profit","—")}</span>'
                    f'<span style="background:rgba(248,113,113,0.12);color:#f87171;'
                    f'padding:5px 12px;border-radius:6px;font-size:12px;">'
                    f'Max Loss: ${opt.get("max_loss","—")}</span>'
                    f'<span style="background:rgba(251,191,36,0.12);color:#fbbf24;'
                    f'padding:5px 12px;border-radius:6px;font-size:12px;">'
                    f'Breakeven: {opt.get("breakeven","—")}</span>'
                    f'</div>'

                    f'{news_html}'
                    f'</div></div>'  # /body, /card
                )

            # Combined AI stock analysis
            if stock_ai:
                html += (
                    '<div style="background:#111827;border:1px solid #374151;'
                    'border-radius:12px;padding:16px 20px;margin-top:4px;">'
                    '<div style="font-size:11px;color:#60a5fa;font-weight:700;'
                    'letter-spacing:1.5px;margin-bottom:10px;">'
                    '🤖 ניתוח מניות — Tastytrade Analyst</div>'
                    f'<div style="font-size:13px;line-height:1.9;color:#e2e8f0;">{stock_ai}</div>'
                    '</div>'
                )

            html += '</div>'  # /stocks section

        # ── Market context footer ──────────────────────────────────────
        macro      = report.get("macro_context") or {}
        fed_rate   = macro.get("fed_rate", "N/A")
        cpi_yoy    = macro.get("cpi_yoy",  "N/A")
        macro_reg  = macro.get("regime",   "")
        macro_note = macro.get("notes",    "")
        regime_color = (
            "#f87171" if macro_reg in ("HIGH_RATE", "ELEVATED") else
            "#4ade80" if macro_reg == "LOW_RATE" else "#fbbf24"
        )

        html += (
            '<div style="background:#111827;border:1px solid #374151;border-radius:12px;'
            'padding:16px 20px;margin-bottom:20px;">'
            '<div style="font-size:11px;font-weight:700;color:#9ca3af;'
            'letter-spacing:2px;margin-bottom:12px;">🌡️ MARKET CONTEXT &amp; MACRO</div>'
            '<div style="display:flex;gap:20px;flex-wrap:wrap;font-size:13px;margin-bottom:10px;">'
            f'<div style="color:#e2e8f0;"><b>VIX:</b> <span style="color:{vix_color}">{vix}</span></div>'
            f'<div style="color:#e2e8f0;"><b>SPX:</b> <span style="color:white">{spx}</span></div>'
            f'<div style="color:#e2e8f0;"><b>Fed Rate:</b> <span style="color:{regime_color}">{fed_rate}%</span></div>'
            f'<div style="color:#e2e8f0;"><b>CPI YoY:</b> <span style="color:#fbbf24">{cpi_yoy}%</span></div>'
            f'<div style="color:#e2e8f0;"><b>Regime:</b> <span style="color:{regime_color}">{macro_reg}</span></div>'
            '</div>'
            + (
                f'<div style="background:#0f172a;border-right:2px solid {regime_color};'
                f'padding:8px 12px;border-radius:4px;font-size:12px;color:#cbd5e1;">'
                f'{macro_note}</div>'
                if macro_note else ""
            )
            + '</div>'

            # Footer
            '<div style="text-align:center;font-size:11px;color:#4b5563;padding-bottom:10px;">'
            'Daily Options Brief · Tastytrade Methodology · Powered by AI + XGBoost · '
            'Not investment advice — manage your own risk</div>'
            '</div>'
        )

        try:
            resend.Emails.send({
                "from":    settings.FROM_EMAIL,
                "to":      [settings.ALERT_TO_EMAIL],
                "subject": subject,
                "html":    html,
            })
            print(f"✅ Daily Options Brief sent (VIX={vix}, stocks={len(stocks)}).")
        except Exception as e:
            print(f"❌ Options email send error: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Deep Dive Report — on-demand single-ticker research note
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def send_deep_dive_report(
        data: dict,
        ai_result: dict,
        to_email: str | None = None,
    ) -> None:
        """
        Send a professional Deep Dive research report for a single ticker.

        Args:
            data      : merged dict from AnalysisService.analyze()
            ai_result : dict with 'full_analysis', 'score', 'recommendation'
            to_email  : override recipient (default: settings.ALERT_TO_EMAIL)
        """
        ticker     = data.get("ticker", "?")
        price      = data.get("current_price", "N/A")
        mkt_cap    = data.get("market_cap", 0) or 0
        rsi        = data.get("rsi", "N/A")
        sma50      = data.get("sma50", "N/A")
        sma200     = data.get("sma200", "N/A")
        w52_low    = data.get("week_52_low", "N/A")
        w52_high   = data.get("week_52_high", "N/A")
        dte        = data.get("debt_to_equity", "N/A")
        curr_ratio = data.get("current_ratio", "N/A")
        pe         = data.get("pe_ratio", "N/A")
        short_pct  = data.get("short_pct_float", "N/A")
        inst_pct   = data.get("inst_pct_held", "N/A")
        news       = data.get("news", [])
        timestamp  = data.get("timestamp", "")[:10]

        score      = ai_result.get("score", 0)
        rec        = ai_result.get("recommendation", "HOLD")
        analysis   = ai_result.get("full_analysis", "")

        # ── Colour scheme ──────────────────────────────────────────────────
        NAVY   = "#1e3a5f"
        WHITE  = "#ffffff"
        LIGHT  = "#f4f6f9"
        BORDER = "#dde3ed"

        rec_color = {"BUY": "#15803d", "SELL": "#dc2626"}.get(rec, "#b45309")
        rec_bg    = {"BUY": "#dcfce7", "SELL": "#fee2e2"}.get(rec, "#fef9c3")

        score_color = (
            "#15803d" if score >= 70
            else "#dc2626" if score <= 40
            else "#b45309"
        )

        def _fmt_cap(v):
            try:
                v = float(v)
                return f"${v/1e9:.1f}B" if v >= 1e9 else f"${v/1e6:.0f}M"
            except Exception:
                return "N/A"

        def _news_rows():
            if not news:
                return "<li style='color:#6b7280;'>No recent headlines found.</li>"
            rows = ""
            for n in news[:5]:
                h = n.get("headline", "")
                s = n.get("source", "")
                dt = ""
                pub = n.get("published_at")
                if pub:
                    try:
                        dt = pub.strftime("%b %d") if hasattr(pub, "strftime") else str(pub)[:10]
                    except Exception:
                        pass
                rows += (
                    f"<li style='margin-bottom:8px;padding-bottom:8px;"
                    f"border-bottom:1px solid {BORDER};'>"
                    f"<span style='color:#374151;font-size:13px;'>{h}</span>"
                    f"<span style='color:#9ca3af;font-size:11px;margin-right:8px;'>"
                    f" — {s} {dt}</span></li>"
                )
            return rows

        def _analysis_html():
            """Convert the markdown-like analysis to simple HTML paragraphs."""
            if not analysis:
                return "<p>ניתוח לא זמין.</p>"
            html_out = ""
            for line in analysis.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("## "):
                    html_out += (
                        f"<h3 style='color:{NAVY};font-size:16px;margin:20px 0 8px;"
                        f"padding-bottom:6px;border-bottom:2px solid {BORDER};'>"
                        f"{stripped[3:]}</h3>"
                    )
                elif stripped.startswith("| "):
                    # Table row
                    cells = [c.strip() for c in stripped.split("|")[1:-1]]
                    if all(set(c) <= set("-: ") for c in cells):
                        continue  # skip separator row
                    html_out += "<tr>"
                    for i, c in enumerate(cells):
                        bg = LIGHT if i == 0 else WHITE
                        html_out += (
                            f"<td style='padding:8px 12px;border:1px solid {BORDER};"
                            f"font-size:13px;background:{bg};'>{c}</td>"
                        )
                    html_out += "</tr>"
                elif stripped.startswith("**") and stripped.endswith("**"):
                    html_out += (
                        f"<p style='font-weight:bold;color:{NAVY};margin:10px 0 4px;'>"
                        f"{stripped[2:-2]}</p>"
                    )
                else:
                    # Replace inline **bold**
                    import re as _re
                    line_html = _re.sub(
                        r"\*\*(.+?)\*\*",
                        r"<strong>\1</strong>",
                        stripped,
                    )
                    html_out += (
                        f"<p style='color:#374151;font-size:14px;line-height:1.7;"
                        f"margin:4px 0;'>{line_html}</p>"
                    )
            return html_out

        # Wrap table rows in a <table> tag
        import re as _re
        analysis_html = _analysis_html()
        analysis_html = _re.sub(
            r"(<tr>.*?</tr>)+",
            lambda m: (
                f"<table style='width:100%;border-collapse:collapse;"
                f"margin:12px 0;font-size:13px;'>{m.group(0)}</table>"
            ),
            analysis_html,
            flags=_re.DOTALL,
        )

        html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Deep Dive — {ticker}</title>
</head>
<body style="margin:0;padding:0;background:{LIGHT};font-family:'Segoe UI',Arial,sans-serif;direction:rtl;">

<!-- Wrapper -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:{LIGHT};padding:24px 0;">
<tr><td align="center">
<table width="660" cellpadding="0" cellspacing="0" style="background:{WHITE};border-radius:8px;
  overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">

  <!-- ── HEADER BAND ─────────────────────────────────────────────────── -->
  <tr>
    <td style="background:{NAVY};padding:28px 32px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <p style="margin:0;color:rgba(255,255,255,0.65);font-size:12px;letter-spacing:2px;
               text-transform:uppercase;">Goldman Sachs Style Deep Dive</p>
            <h1 style="margin:6px 0 0;color:{WHITE};font-size:32px;font-weight:700;">
              {ticker}</h1>
            <p style="margin:4px 0 0;color:rgba(255,255,255,0.75);font-size:14px;">
              {timestamp} &nbsp;|&nbsp; מחיר: <strong>${price}</strong>
              &nbsp;|&nbsp; שווי שוק: <strong>{_fmt_cap(mkt_cap)}</strong>
            </p>
          </td>
          <td align="left" style="vertical-align:top;">
            <!-- Score badge -->
            <div style="background:rgba(255,255,255,0.12);border-radius:8px;
              padding:14px 20px;text-align:center;display:inline-block;">
              <p style="margin:0;color:rgba(255,255,255,0.7);font-size:11px;">SCORE</p>
              <p style="margin:2px 0;color:{WHITE};font-size:34px;font-weight:800;
                line-height:1;">{score}</p>
              <p style="margin:0;color:rgba(255,255,255,0.7);font-size:11px;">/ 100</p>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── RECOMMENDATION BANNER ─────────────────────────────────────── -->
  <tr>
    <td style="background:{rec_bg};padding:16px 32px;border-bottom:3px solid {rec_color};">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <span style="font-size:22px;font-weight:800;color:{rec_color};">
              ● {rec}</span>
            <span style="font-size:14px;color:#6b7280;margin-right:12px;">
              — המלצת אנליסט</span>
          </td>
          <td align="left">
            <span style="font-size:13px;color:#6b7280;">52W: ${w52_low} – ${w52_high}</span>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── KPI CARDS ROW ─────────────────────────────────────────────── -->
  <tr>
    <td style="padding:24px 32px 8px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <!-- RSI -->
          <td width="33%" style="padding:0 8px 0 0;">
            <div style="background:{LIGHT};border-radius:6px;padding:14px 16px;
              border-right:4px solid {NAVY};">
              <p style="margin:0;font-size:11px;color:#9ca3af;text-transform:uppercase;
                letter-spacing:1px;">RSI (14)</p>
              <p style="margin:4px 0 0;font-size:24px;font-weight:700;color:{NAVY};">
                {rsi}</p>
              <p style="margin:2px 0 0;font-size:11px;color:#6b7280;">
                {'⚠️ קנוי יתר' if isinstance(rsi, (int,float)) and float(rsi)>70
                 else '⚠️ מכור יתר' if isinstance(rsi, (int,float)) and float(rsi)<30
                 else '✅ נייטרלי'}</p>
            </div>
          </td>
          <!-- SMA -->
          <td width="33%" style="padding:0 4px;">
            <div style="background:{LIGHT};border-radius:6px;padding:14px 16px;
              border-right:4px solid #0ea5e9;">
              <p style="margin:0;font-size:11px;color:#9ca3af;text-transform:uppercase;
                letter-spacing:1px;">SMA 50 / 200</p>
              <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:{NAVY};">
                ${sma50}</p>
              <p style="margin:2px 0 0;font-size:13px;color:#6b7280;">
                200d: ${sma200}</p>
            </div>
          </td>
          <!-- Fundamentals -->
          <td width="33%" style="padding:0 0 0 8px;">
            <div style="background:{LIGHT};border-radius:6px;padding:14px 16px;
              border-right:4px solid #8b5cf6;">
              <p style="margin:0;font-size:11px;color:#9ca3af;text-transform:uppercase;
                letter-spacing:1px;">P/E | D/E</p>
              <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:{NAVY};">
                {pe} | {dte}</p>
              <p style="margin:2px 0 0;font-size:13px;color:#6b7280;">
                Current Ratio: {curr_ratio}</p>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── INSTITUTIONAL ROW ─────────────────────────────────────────── -->
  <tr>
    <td style="padding:8px 32px 20px;">
      <table width="100%" cellpadding="0" cellspacing="0"
        style="background:{LIGHT};border-radius:6px;padding:12px 16px;">
        <tr>
          <td style="padding:8px 16px;border-left:1px solid {BORDER};">
            <p style="margin:0;font-size:11px;color:#9ca3af;">SHORT % FLOAT</p>
            <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:{NAVY};">
              {short_pct}%</p>
          </td>
          <td style="padding:8px 16px;border-left:1px solid {BORDER};">
            <p style="margin:0;font-size:11px;color:#9ca3af;">INST. OWNED</p>
            <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:{NAVY};">
              {inst_pct}%</p>
          </td>
          <td style="padding:8px 16px;">
            <p style="margin:0;font-size:11px;color:#9ca3af;">SQUEEZE RISK</p>
            <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:{NAVY};">
              {data.get("short_squeeze_risk","N/A")}</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── AI ANALYSIS ───────────────────────────────────────────────── -->
  <tr>
    <td style="padding:0 32px 24px;">
      <h2 style="color:{NAVY};font-size:18px;margin:0 0 16px;padding-bottom:8px;
        border-bottom:2px solid {NAVY};">ניתוח אנליסט — Goldman Sachs Style</h2>
      <div style="font-size:14px;line-height:1.75;color:#374151;">
        {analysis_html}
      </div>
    </td>
  </tr>

  <!-- ── NEWS HEADLINES ────────────────────────────────────────────── -->
  <tr>
    <td style="padding:0 32px 24px;">
      <h2 style="color:{NAVY};font-size:18px;margin:0 0 16px;padding-bottom:8px;
        border-bottom:2px solid {BORDER};">📰 חדשות אחרונות</h2>
      <ul style="margin:0;padding:0;list-style:none;">
        {_news_rows()}
      </ul>
    </td>
  </tr>

  <!-- ── FOOTER ────────────────────────────────────────────────────── -->
  <tr>
    <td style="background:{NAVY};padding:16px 32px;">
      <p style="margin:0;color:rgba(255,255,255,0.5);font-size:11px;text-align:center;">
        {ticker} Deep Dive — Generated {timestamp} &nbsp;|&nbsp;
        Not investment advice. Manage your own risk.
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""

        subject = f"🔬 Deep Dive: {ticker} — {rec} | Score {score}/100"
        recipient = to_email or settings.ALERT_TO_EMAIL

        try:
            resend.Emails.send({
                "from":    settings.FROM_EMAIL,
                "to":      [recipient],
                "subject": subject,
                "html":    html,
            })
            logger.info("Deep Dive report sent: %s → %s (score=%d rec=%s)", ticker, recipient, score, rec)
        except Exception as exc:
            logger.exception("Deep Dive email send failed for %s: %s", ticker, exc)