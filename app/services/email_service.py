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

class EmailService:
    @staticmethod
    def format_number(num):
        if not num: return "0"
        if abs(num) > 1_000_000_000: return f"${num/1_000_000_000:.2f}B"
        if abs(num) > 1_000_000: return f"${num/1_000_000:.1f}M"
        return f"${num:,.0f}"

    @staticmethod
    def send_report(stock_opportunities, general_news):
        if not stock_opportunities and not general_news: return
        if not settings.RESEND_API_KEY: return

        subject = f"🚀 דוח מסחר: {len(stock_opportunities)} הזדמנויות"

        html_body = """
        <div dir="rtl" style="font-family: 'Segoe UI', sans-serif; max-width: 750px; margin: 0 auto; background: #f4f6f8; padding: 20px;">
            <h2 style="background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                📊 דוח מסחר היברידי (AI + SMA150)
            </h2>
        """

        if stock_opportunities:
            for opp in stock_opportunities:
                fin = opp['financials']
                rev = fin.get('revenue', {})
                ni = fin.get('net_income', {})
                eff = fin.get('efficiency', {}) # שליפת נתוני התייעלות

                tech_signal = fin.get('technical_signal', 'ללא איתות')
                trend_status = fin.get('trend_status', 'ללא מידע')
                vol_ratio = fin.get('volume_ratio', 1.0)

                # צבעים לטכני
                signal_bg = "#8e44ad" if "SMA150" in str(tech_signal) else ("#d35400" if "פריצת" in str(tech_signal) else "#7f8c8d")
                trend_color = "#27ae60" if "מעל SMA150" in trend_status else "#c0392b"

                # צבעים לווליום
                vol_text = "ווליום רגיל"
                vol_color = "#7f8c8d"
                if vol_ratio > 1.5:
                    vol_text = f"🔥 ווליום גבוה (x{vol_ratio})"
                    vol_color = "#d35400"
                elif vol_ratio > 3.0:
                    vol_text = f"🚀 ווליום מטורף (x{vol_ratio})"
                    vol_color = "#c0392b"

                # --- לוגיקה לתצוגת התייעלות ---
                eff_curr = eff.get('curr')
                eff_prev = eff.get('prev')
                eff_display = "-"
                eff_color = "black"

                if isinstance(eff_curr, (int, float)) and isinstance(eff_prev, (int, float)):
                    # אם היחס ירד (פחות הוצאות על הכנסות) -> זה טוב!
                    if eff_curr < eff_prev:
                        eff_display = "✅ שיפור (התייעלות)"
                        eff_color = "green"
                    elif eff_curr > eff_prev:
                        eff_display = "⚠️ הרעה (בזבזנות)"
                        eff_color = "red"
                    else:
                        eff_display = "ללא שינוי"

                html_body += f"""
                <div style="background: white; border-radius: 12px; padding: 25px; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">

                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; padding-bottom: 10px;">
                        <div>
                            <h1 style="margin: 0; color: #2c3e50;">{opp['ticker']} <span style="font-size:16px; color:#555;">${opp['price']}</span></h1>
                        </div>
                        <div style="background: #27ae60; color: white; padding: 5px 12px; border-radius: 20px; font-weight: bold;">
                            Score: {int(opp['score'])}
                        </div>
                    </div>

                    <div style="display:flex; gap:10px; flex-wrap:wrap; margin: 15px 0;">
                        <span style="background:{signal_bg}; color:white; padding:4px 10px; border-radius:4px; font-weight:bold; font-size:13px;">{tech_signal}</span>
                        <span style="background:{trend_color}; color:white; padding:4px 10px; border-radius:4px; font-weight:bold; font-size:13px;">{trend_status}</span>
                        <span style="background:{vol_color}; color:white; padding:4px 10px; border-radius:4px; font-weight:bold; font-size:13px;">{vol_text}</span>
                    </div>

                    <div style="background: #f8f9fa; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; line-height: 1.5;">
                        <b>🏢 פרופיל חברה:</b> {opp.get('ai_hebrew_desc', 'אין תיאור זמין')}
                    </div>

                    <div style="margin-bottom: 15px;">
                        <b style="color:#d35400;">📰 כותרת:</b> {opp['headline']}
                    </div>

                    <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                        <b style="color:#1565c0;">💡 ניתוח AI:</b>
                        <div style="margin-top:5px; font-size:14px;">{opp.get('ai_analysis', '...')}</div>
                    </div>

                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <tr style="background: #eee;">
                            <th style="padding:8px; text-align:right;">נתון</th>
                            <th style="padding:8px; text-align:right;">נוכחי</th>
                            <th style="padding:8px; text-align:right;">קודם</th>
                            <th style="padding:8px; text-align:right;">מגמה</th>
                        </tr>
                        <tr style="border-bottom:1px solid #eee;">
                            <td style="padding:8px;">הכנסות</td>
                            <td style="padding:8px;">{EmailService.format_number(rev.get('curr', 0))}</td>
                            <td style="padding:8px;">{EmailService.format_number(rev.get('prev', 0))}</td>
                            <td style="padding:8px; color:{'green' if rev.get('change',0) > 0 else 'red'}">{rev.get('change', 0)}%</td>
                        </tr>
                        <tr style="border-bottom:1px solid #eee;">
                            <td style="padding:8px;">רווח נקי</td>
                            <td style="padding:8px;">{EmailService.format_number(ni.get('curr', 0))}</td>
                            <td style="padding:8px;">{EmailService.format_number(ni.get('prev', 0))}</td>
                            <td style="padding:8px; color:{'green' if ni.get('change',0) > 0 else 'red'}">{ni.get('change', 0)}%</td>
                        </tr>
                        <tr>
                            <td style="padding:8px;">
                                <b>יחס הוצאות</b><br>
                                <span style="font-size:11px; color:#777;">(נמוך=טוב)</span>
                            </td>
                            <td style="padding:8px;">{eff_curr}%</td>
                            <td style="padding:8px;">{eff_prev}%</td>
                            <td style="padding:8px; color:{eff_color}; font-weight:bold;">{eff_display}</td>
                        </tr>
                    </table>
                </div>
                """

        if general_news:
             html_body += "<h3 style='margin-top:30px; border-bottom:2px solid #ccc;'>חדשות כלליות</h3>"
             for news in general_news:
                html_body += f"<div style='margin-bottom:10px; font-size:13px;'>• <b>{news['headline']}</b> <a href='{news['url']}'>קרא עוד</a></div>"

        html_body += "</div>"

        try:
            resend.Emails.send({
                "from": settings.FROM_EMAIL,
                "to": [settings.ALERT_TO_EMAIL],
                "subject": subject,
                "html": html_body
            })
            print(f"✅ Email sent!")
        except Exception as e:
            print(f"❌ Resend Error: {e}")