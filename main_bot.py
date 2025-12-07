import requests
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import telegram
import time
import schedule

# የእርስዎ የግል ሚስጥራዊ ቁልፎች እዚህ ይገባሉ!
BOT_TOKEN = '8522122012:AAFjNAlsEN2wIoWts-wnYLkJdETEQLsgtzs' 
CHAT_ID = '7168361565'
ALPHA_VANTAGE_API_KEY = 'HN3CWURNZODZNOQ3'

# የትንተና መለኪያዎች (Parameters)
RSI_OVERSOLD = 30 # የግዢ ዞን ምልክት
RSI_OVERBOUGHT = 70 # የሽያጭ ዞን ምልክት
MA_PERIOD = 50 # 50-EMAን ለመጠቀም
def fetch_xauusd_data():
    # ከXAU ወደ USD የዕለታዊ የዋጋ መረጃን የሚጠይቅ API
    url = f'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=XAU&to_symbol=USD&outputsize=full&apikey={ALPHA_VANTAGE_API_KEY}'
    
    try:
        r = requests.get(url)
        data = r.json()
        
        data_series = data.get('Time Series FX (Daily)')
        if not data_series:
            return None
            
        # መረጃውን ወደ Pandas DataFrame መቀየር
        data_df = pd.DataFrame(data_series).T
        data_df.columns = ['open', 'high', 'low', 'close']
        data_df = data_df.astype(float)
        
        # የመጨረሻዎቹን 100 የዋጋ አሞሌዎች (bars) ለትንተና መጠቀም
        return data_df.iloc[-100:] 
    except Exception as e:
        # ስህተት ሲገጥም በኮንሶል (console) ላይ ማተም
        print(f"Error fetching data: {e}")
        return None
def generate_analysis_signal(data_df):
    if data_df is None or data_df.empty:
        return "⚠️ Data Fetch Failed. Cannot generate signal."
    
    # 1. RSI (14-period) ስሌት - ለኃይል መለኪያ (Momentum)
    data_df['RSI'] = RSIIndicator(data_df['close'], window=14).rsi()
    # 2. EMA (50-period) ስሌት - ለዋናው አቅጣጫ/ትሬንድ መለያ (Trend)
    data_df['EMA_50'] = EMAIndicator(data_df['close'], window=MA_PERIOD).ema_indicator()
    
    # የመጨረሻ የዋጋ እና አመልካች ዋጋዎችን ማግኘት
    latest_close = data_df['close'].iloc[-1]
    latest_rsi = data_df['RSI'].iloc[-1]
    latest_ema = data_df['EMA_50'].iloc[-1]
    
    signal = "NEUTRAL 🟡"
    reason = "Market is consolidating. Wait for a clear zone."
    
    # --- የ BUY/SELL ዞን ፍቺ ሎጂክ (ምርጡ የትሬዲንግ እውቀት) ---
    # Buy Zone Logic: RSI ከ30 በታች እና ዋጋ ከ50-EMA በላይ (ከታች ወደ ላይ የሚመጣ ጥሩ ግዢ)
    if latest_rsi < RSI_OVERSOLD and latest_close > latest_ema:
        signal = "STRONG BUY 🟢"
        reason = f"RSI ({latest_rsi:.2f}) is in **Oversold Zone** (<{RSI_OVERSOLD}). Price is above 50-EMA. High probability for rebound."
        
    # Sell Zone Logic: RSI ከ70 በላይ እና ዋጋ ከ50-EMA በታች (ከላይ ወደ ታች የሚመጣ ጥሩ ሽያጭ)
    elif latest_rsi > RSI_OVERBOUGHT and latest_close < latest_ema:
        signal = "STRONG SELL 🔴"
        reason = f"RSI ({latest_rsi:.2f}) is in **Overbought Zone** (>{RSI_OVERBOUGHT}). Price is below 50-EMA. High probability for pullback."
        
    
    # የቴሌግራም መልእክት ቅርፅ
    message = (
        f"**🚨 XAUUSD Daily Analysis 🚨**\n"
        f"**SIGNAL:** {signal}\n"
        f"**Price:** ${latest_close:.2f}\n"
        f"**RSI (14):** {latest_rsi:.2f}\n"
        f"**50-EMA:** ${latest_ema:.2f}\n"
        f"----------------------\n"
        f"**Analysis:** {reason}\n"
        f"Time: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')} (Render Server Time)"
    )
    return message
# --- 3. የቴሌግራም መልእክት የመላክ ተግባር ---
def send_telegram_message(message):
    try:
        bot = telegram.Bot(token=BOT_TOKEN)
        # መልዕክቱን በMarkdown ቅርጽ ይልካል
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
        print("Telegram Message Sent Successfully.")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

# --- 4. ዋናው የሥራ ማስኬጃ (Job Function) ---
def daily_analysis_job():
    print("--- Running Analysis Job ---")
    data = fetch_xauusd_data()
    signal_message = generate_analysis_signal(data)
    send_telegram_message(signal_message)
    print("--- Analysis Job Finished ---")

# --- 5. የጊዜ ሰሌዳ አዘጋጅ (Scheduler) ---
def start_scheduler():
    # በየቀኑ በዓለም አቀፍ ሰዓት (UTC) በ10:00 AM እንዲሰራ (ይህም ለብዙ የግብይት ገበያዎች መክፈቻ ተስማሚ ነው)
    schedule.every().day.at("10:00").do(daily_analysis_job) 
    
    print("Scheduler started. Waiting for next run...")
    while True:
        schedule.run_pending()
        time.sleep(1) # በየ 1 ሰከንዱ የጊዜ ሰሌዳውን ይፈትሻል

if __name__ == '__main__':
    daily_analysis_job() # ቦቱ ሲጀመር ለመጀመሪያ ጊዜ ወዲያው እንዲሰራ
    start_scheduler()
