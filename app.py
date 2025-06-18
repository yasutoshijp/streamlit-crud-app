import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from google.cloud import texttospeech
import google.api_core.exceptions

# --- ページ設定 ---
st.set_page_config(page_title="Google TTS連携 読み上げアプリ", layout="wide")
st.title("☁️ Google Cloud TTS連携 読み上げアプリ")
st.caption("入力したテキストをGoogleの高品質な音声に変換し、スプレッドシートで管理します。")

# --- Google Cloud認証 ---
# st.connection("gsheets") で使われている認証情報を再利用
try:
    # credentials引数にStreamlitのSecrets機能で読み込んだ認証情報を渡す
    gcp_credentials = st.connection("gsheets", type="gsheets")._credentials
    client = texttospeech.TextToSpeechClient(credentials=gcp_credentials)
except Exception as e:
    st.error(f"Google Cloudへの認証に失敗しました。Secretsの設定を確認してください。: {e}")
    st.stop()


# --- Google Cloud TTS関連の関数 ---

@st.cache_data(ttl=3600) # 1時間キャッシュする
def get_google_voices():
    """利用可能な音声のリストを取得する"""
    try:
        voices_response = client.list_voices(language_code="ja-JP")
        return voices_response.voices
    except google.api_core.exceptions.GoogleAPICallError as e:
        st.error(f"音声リストの取得に失敗しました: {e}")
        return []

def generate_voice_google(text, voice_name):
    """指定されたテキストと音声名から音声データを生成する"""
    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="ja-JP", name=voice_name
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return response.audio_content
    except google.api_core.exceptions.GoogleAPICallError as e:
        st.error(f"音声の生成に失敗しました: {e}")
        return None

# --- データ管理関数 (スプレッドシート) ---
# (ここは前回のコードから変更なし)
try:
    conn = st.connection("gsheets")
except Exception as e:
    st.error("Googleスプレッドシートへの接続に失敗しました。Secretsを確認してください。")
    st.stop()

def load_data(worksheet_name="音声データ_google"):
    try:
        sheet = conn.read(worksheet=worksheet_name, ttl=5)
        sheet = sheet.dropna(how="all")
        return sheet.to_dict('records')
    except Exception:
        return []

def save_data(worksheet_name="音声データ_google"):
    try:
        df = pd.DataFrame(st.session_state.data)
        conn.clear(worksheet=worksheet_name)
        conn.update(worksheet=worksheet_name, data=df)
    except Exception as e:
        st.error(f"スプレッドシートへの書き込みに失敗しました: {e}")

# --- st.session_stateの初期化 ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- UI表示 ---
st.header("新しい音声を作成")

voices = get_google_voices()
if voices:
    # 音声リストを整形
    voice_options = {f"{v.name} ({v.ssml_gender.name})": v.name for v in voices}
    
    selected_voice_name_display = st.selectbox(
        "音声（ボイス）を選択してください",
        options=voice_options.keys()
    )
    
    text_to_speak = st.text_area("読み上げるテキストを入力", height=150)

    if st.button("音声を作成して保存"):
        if text_to_speak:
            voice_name = voice_options[selected_voice_name_display]
            
            with st.spinner("音声を生成中です..."):
                audio_data = generate_voice_google(text_to_speak, voice_name)

            if audio_data:
                new_item = {
                    "id": str(uuid.uuid4()),
                    "text": text_to_speak,
                    "voice_name": voice_name,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.data.insert(0, new_item)
                save_data()
                st.success("音声の作成と保存が完了しました！")
                st.audio(audio_data, format="audio/mp3") # すぐに再生できるようにする
                st.rerun()
        else:
            st.warning("テキストを入力してください。")
else:
    st.warning("Googleから音声リストを取得できませんでした。API設定を確認してください。")

st.divider()
st.header("作成済み音声一覧")

if not st.session_state.data:
    st.info("まだ音声データがありません。")
else:
    for i, item in enumerate(st.session_state.data):
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text_area(f"text_{item['id']}", value=item['text'], disabled=True, height=100,
                             label=f"📝 **テキスト** (作成日時: {item.get('created_at', 'N/A')})")
                st.caption(f"ボイス: {item['voice_name']}")
            with col2:
                if st.button("この音声を聞く", key=f"play_{item['id']}"):
                    with st.spinner("音声データを生成中..."):
                        audio_data = generate_voice_google(item['text'], item['voice_name'])
                        if audio_data:
                            st.audio(audio_data, format="audio/mp3")
                
                st.download_button(
                    label="MP3でダウンロード",
                    data=generate_voice_google(item['text'], item['voice_name']) or b"",
                    file_name=f"voice_{item['id']}.mp3",
                    mime="audio/mp3",
                    key=f"download_{item['id']}"
                )
                if st.button("🗑️ 削除", key=f"delete_{item['id']}", type="primary"):
                    st.session_state.data.pop(i)
                    save_data()
                    st.success(f"ID: {item['id'][:6]}... を削除しました。")
                    st.rerun()