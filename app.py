# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from google.cloud import texttospeech
import google.api_core.exceptions
import sys
import os

# エンコーディングの設定を最初に行う
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 環境変数でエンコーディングを設定
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# 重要: st-gsheets-connectionを明示的にインポート
try:
    from streamlit_gsheets import GSheetsConnection
    st.write("✅ st-gsheets-connection が正常にインポートされました")
except ImportError as e:
    st.error(f"❌ st-gsheets-connection のインポートに失敗: {e}")
    st.stop()

# ページ設定
st.set_page_config(
    page_title="音声生成CRUDアプリ",
    page_icon="🎵",
    layout="wide"
)

# Google Sheets接続の初期化
@st.cache_resource
def init_gsheets_connection():
    """Google Sheetsへの接続を初期化"""
    try:
        # デバッグ情報の表示
        st.write("🔍 デバッグ: 接続初期化を開始...")
        
        # _REGISTRYアクセスを安全に行う
        try:
            if hasattr(st.connection, '_REGISTRY'):
                st.write(f"🔍 利用可能な接続タイプ: {st.connection._REGISTRY}")
            else:
                st.write("🔍 _REGISTRYにアクセスできません（正常な場合があります）")
        except Exception as reg_error:
            st.write(f"🔍 _REGISTRY確認中にエラー: {reg_error}")
        
        # gsheets接続を試行 - より安全な方法
        conn = st.connection("gsheets", type=GSheetsConnection)
        st.write("✅ Google Sheets接続が成功しました")
        return conn
    except Exception as e:
        st.error(f"❌ Google Sheets接続エラー: {str(e)}")
        st.write(f"🔍 エラーの詳細: {type(e).__name__}")
        return None

# Text-to-Speech クライアントの初期化
@st.cache_resource
def init_tts_client():
    """Text-to-Speech クライアントを初期化"""
    try:
        # Google Sheetsの接続情報から実際のサービスアカウント認証情報を取得
        gsheets_info = st.secrets["connections"]["gsheets"]
        
        # サービスアカウント情報から認証情報を作成
        from google.oauth2 import service_account
        import json
        
        # 認証情報を取得する（サーバーとローカルで構造が異なる）
        credentials_dict = None
        
        # パターン1: credentialsサブセクションがある場合（ローカル）
        if 'credentials' in gsheets_info:
            try:
                credentials_info = gsheets_info['credentials']
                if hasattr(credentials_info, 'to_dict'):
                    credentials_dict = credentials_info.to_dict()
                elif hasattr(credentials_info, '_data'):
                    credentials_dict = dict(credentials_info._data)
                else:
                    credentials_dict = dict(credentials_info)
                st.write("🔍 credentialsサブセクションから認証情報を取得しました")
            except Exception as e:
                st.write(f"🔍 credentialsサブセクションアクセスエラー: {e}")
        
        # パターン2: 直接gsheets_infoにサービスアカウント情報がある場合（サーバー）
        if credentials_dict is None:
            try:
                # 必要なキーが直接存在するかチェック
                required_keys = ['client_email', 'private_key', 'project_id']
                if all(key in gsheets_info for key in required_keys):
                    credentials_dict = dict(gsheets_info)
                    st.write("🔍 直接アクセスから認証情報を取得しました")
                else:
                    missing_keys = [key for key in required_keys if key not in gsheets_info]
                    st.write(f"🔍 必要なキーが不足: {missing_keys}")
            except Exception as e:
                st.write(f"🔍 直接アクセスエラー: {e}")
        
        if credentials_dict is None:
            raise ValueError("認証情報を取得できませんでした")
        
        # 認証情報をログ出力（プライベートキーは除外）
        safe_keys = [k for k in credentials_dict.keys() if k != 'private_key']
        st.write(f"🔍 取得した認証情報のキー: {safe_keys}")
        
        # 必要なキーの存在確認
        required_keys = ['client_email', 'private_key', 'project_id']
        missing_keys = [key for key in required_keys if key not in credentials_dict]
        if missing_keys:
            raise ValueError(f"必要なキーが不足しています: {missing_keys}")
        
        # Text-to-Speech用のスコープを設定
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        client = texttospeech.TextToSpeechClient(credentials=credentials)
        st.write("✅ Text-to-Speech クライアントが正常に初期化されました")
        return client
            
    except Exception as e:
        st.error(f"❌ Text-to-Speech クライアントの初期化に失敗: {str(e)}")
        st.write(f"🔍 エラータイプ: {type(e).__name__}")
        
        # 詳細なデバッグ情報
        try:
            gsheets_info = st.secrets["connections"]["gsheets"]
            st.write(f"🔍 gsheets_info のキー: {list(gsheets_info.keys())}")
            if 'credentials' in gsheets_info:
                cred_info = gsheets_info['credentials']
                st.write(f"🔍 credentials のタイプ: {type(cred_info)}")
                if hasattr(cred_info, 'keys'):
                    safe_cred_keys = [k for k in cred_info.keys() if k != 'private_key']
                    st.write(f"🔍 credentials のキー: {safe_cred_keys}")
                
                # 個別キーの存在確認
                test_keys = ['client_email', 'project_id', 'private_key']
                for key in test_keys:
                    exists = key in cred_info
                    st.write(f"🔍 {key} exists: {exists}")
        except Exception as debug_error:
            st.write(f"🔍 デバッグ情報取得エラー: {debug_error}")
        
        return None

# データベース操作関数
def get_all_records(conn):
    """すべてのレコードを取得"""
    try:
        # シート名を明示的に指定
        worksheet_name = "シート1"
        
        # まず最小限のデータ取得を試行
        with st.spinner("データを読み込み中..."):
            df = conn.read(worksheet=worksheet_name, usecols=list(range(7)), ttl=5)
        
        # デバッグ情報を最小限に抑制
        st.write(f"Data shape: {df.shape}")
        
        if not df.empty:
            # カラム名を安全に表示
            col_names = []
            for col in df.columns:
                try:
                    # 日本語カラム名を安全に処理
                    col_str = str(col).encode('ascii', errors='replace').decode('ascii')
                    col_names.append(col_str)
                except:
                    col_names.append(f"column_{len(col_names)}")
            
            st.write(f"Columns: {col_names}")
            
            # データの内容を安全に処理
            for col in df.columns:
                if df[col].dtype == 'object':
                    try:
                        # すべての文字列をASCII安全な形式に変換
                        df[col] = df[col].fillna('').astype(str).apply(
                            lambda x: x.encode('ascii', errors='replace').decode('ascii') if x else ''
                        )
                    except Exception:
                        # 変換に失敗した場合は空文字にする
                        df[col] = ''
        
        return df.dropna(how='all')
        
    except Exception as e:
        # エラーメッセージも安全に表示
        try:
            error_str = str(e).encode('ascii', errors='replace').decode('ascii')
            st.error(f"Data retrieval failed: {error_str}")
        except:
            st.error("Data retrieval failed due to encoding issues")
        
        st.write(f"Error type: {type(e).__name__}")
        
        # 401エラーの特別処理
        error_message = str(e)
        if "401" in error_message or "Unauthorized" in error_message:
            st.info("Please share the Google Sheet with the service account")
            st.code("treamlit-sheet-editor@streamlit-463221.iam.gserviceaccount.com")
        
        return pd.DataFrame()

def add_record(conn, record):
    """新しいレコードを追加"""
    try:
        # 既存データを取得
        existing_df = get_all_records(conn)
        
        # 新しいレコードをDataFrameに変換
        new_df = pd.DataFrame([record])
        
        # データを結合
        if existing_df.empty:
            updated_df = new_df
        else:
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
        
        # スプレッドシートを更新
        conn.update(worksheet="シート1", data=updated_df)
        return True
    except Exception as e:
        st.error(f"データの追加に失敗しました: {str(e)}")
        return False

def update_record(conn, index, record):
    """特定のレコードを更新"""
    try:
        # 既存データを取得
        df = get_all_records(conn)
        
        if index < len(df):
            # 指定されたインデックスの行を更新
            for key, value in record.items():
                if key in df.columns:
                    df.at[index, key] = value
            
            # スプレッドシートを更新
            conn.update(worksheet="シート1", data=df)
            return True
        else:
            st.error("指定されたインデックスが範囲外です")
            return False
    except Exception as e:
        st.error(f"データの更新に失敗しました: {str(e)}")
        return False

def delete_record(conn, index):
    """特定のレコードを削除"""
    try:
        # 既存データを取得
        df = get_all_records(conn)
        
        if index < len(df):
            # 指定されたインデックスの行を削除
            df = df.drop(df.index[index]).reset_index(drop=True)
            
            # スプレッドシートを更新
            conn.update(worksheet="シート1", data=df)
            return True
        else:
            st.error("指定されたインデックスが範囲外です")
            return False
    except Exception as e:
        st.error(f"データの削除に失敗しました: {str(e)}")
        return False

# 音声生成関数
def generate_speech(tts_client, text, language_code="ja-JP", voice_name="ja-JP-Wavenet-A"):
    """テキストから音声を生成"""
    try:
        # テキスト入力を設定
        input_text = texttospeech.SynthesisInput(text=text)
        
        # 音声設定
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )
        
        # オーディオ設定
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        # 音声合成リクエスト
        response = tts_client.synthesize_speech(
            input=input_text,
            voice=voice,
            audio_config=audio_config
        )
        
        return response.audio_content
    except Exception as e:
        st.error(f"音声生成に失敗しました: {str(e)}")
        return None

# メイン関数
def main():
    st.title("🎵 音声生成CRUDアプリ")
    
    # デバッグ情報を表示
    st.sidebar.header("🔍 デバッグ情報")
    
    # Streamlitのバージョンを表示
    st.sidebar.write(f"Streamlit バージョン: {st.__version__}")
    
    # インストールされているパッケージの確認
    try:
        import streamlit_gsheets
        st.sidebar.write(f"✅ streamlit-gsheets: {streamlit_gsheets.__version__}")
    except:
        st.sidebar.write("❌ streamlit-gsheets: 未インストール")
    
    # 接続初期化
    st.header("🔧 接続状態")
    
    with st.spinner("接続を初期化中..."):
        conn = init_gsheets_connection()
        tts_client = init_tts_client()
    
    if not conn:
        st.error("Google Sheetsへの接続に失敗しました。処理を中止します。")
        st.stop()
    
    if not tts_client:
        st.error("Text-to-Speechクライアントの初期化に失敗しました。音声生成機能は利用できません。")
    
    st.success("✅ すべての接続が正常に確立されました")
    
    # サイドバーでモード選択
    mode = st.sidebar.selectbox(
        "操作を選択してください",
        ["データ一覧", "新規追加", "編集", "削除", "音声生成"]
    )
    
    # データ取得
    df = get_all_records(conn)
    
    if mode == "データ一覧":
        st.header("📊 データ一覧")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("データがありません。")
    
    elif mode == "新規追加":
        st.header("➕ 新規データ追加")
        
        with st.form("add_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("タイトル")
                text_content = st.text_area("テキスト内容", height=150)
            
            with col2:
                language = st.selectbox(
                    "言語",
                    ["ja-JP", "en-US", "en-GB"],
                    format_func=lambda x: {"ja-JP": "日本語", "en-US": "英語(US)", "en-GB": "英語(UK)"}[x]
                )
                
                voice_options = {
                    "ja-JP": ["ja-JP-Wavenet-A", "ja-JP-Wavenet-B", "ja-JP-Wavenet-C", "ja-JP-Wavenet-D"],
                    "en-US": ["en-US-Wavenet-A", "en-US-Wavenet-B", "en-US-Wavenet-C", "en-US-Wavenet-D"],
                    "en-GB": ["en-GB-Wavenet-A", "en-GB-Wavenet-B", "en-GB-Wavenet-C", "en-GB-Wavenet-D"]
                }
                
                voice = st.selectbox("音声", voice_options[language])
            
            submitted = st.form_submit_button("追加")
            
            if submitted:
                if title and text_content:
                    # 新しいレコード作成
                    new_record = {
                        "id": str(uuid.uuid4()),
                        "title": title,
                        "text_content": text_content,
                        "language": language,
                        "voice": voice,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    if add_record(conn, new_record):
                        st.success("データが追加されました！")
                        st.rerun()
                    else:
                        st.error("データの追加に失敗しました。")
                else:
                    st.error("タイトルとテキスト内容は必須です。")
    
    elif mode == "編集":
        st.header("✏️ データ編集")
        
        if not df.empty:
            # 編集対象を選択
            selected_index = st.selectbox(
                "編集するデータを選択してください",
                range(len(df)),
                format_func=lambda x: f"{df.iloc[x]['title']} ({df.iloc[x]['created_at']})"
            )
            
            selected_record = df.iloc[selected_index]
            
            with st.form("edit_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    title = st.text_input("タイトル", value=selected_record.get('title', ''))
                    text_content = st.text_area("テキスト内容", value=selected_record.get('text_content', ''), height=150)
                
                with col2:
                    current_language = selected_record.get('language', 'ja-JP')
                    language = st.selectbox(
                        "言語",
                        ["ja-JP", "en-US", "en-GB"],
                        index=["ja-JP", "en-US", "en-GB"].index(current_language) if current_language in ["ja-JP", "en-US", "en-GB"] else 0,
                        format_func=lambda x: {"ja-JP": "日本語", "en-US": "英語(US)", "en-GB": "英語(UK)"}[x]
                    )
                    
                    voice_options = {
                        "ja-JP": ["ja-JP-Wavenet-A", "ja-JP-Wavenet-B", "ja-JP-Wavenet-C", "ja-JP-Wavenet-D"],
                        "en-US": ["en-US-Wavenet-A", "en-US-Wavenet-B", "en-US-Wavenet-C", "en-US-Wavenet-D"],
                        "en-GB": ["en-GB-Wavenet-A", "en-GB-Wavenet-B", "en-GB-Wavenet-C", "en-GB-Wavenet-D"]
                    }
                    
                    current_voice = selected_record.get('voice', voice_options[language][0])
                    voice_index = 0
                    if current_voice in voice_options[language]:
                        voice_index = voice_options[language].index(current_voice)
                    
                    voice = st.selectbox("音声", voice_options[language], index=voice_index)
                
                submitted = st.form_submit_button("更新")
                
                if submitted:
                    if title and text_content:
                        # 更新レコード作成
                        updated_record = {
                            "id": selected_record.get('id', ''),
                            "title": title,
                            "text_content": text_content,
                            "language": language,
                            "voice": voice,
                            "created_at": selected_record.get('created_at', ''),
                            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        if update_record(conn, selected_index, updated_record):
                            st.success("データが更新されました！")
                            st.rerun()
                        else:
                            st.error("データの更新に失敗しました。")
                    else:
                        st.error("タイトルとテキスト内容は必須です。")
        else:
            st.info("編集可能なデータがありません。")
    
    elif mode == "削除":
        st.header("🗑️ データ削除")
        
        if not df.empty:
            # 削除対象を選択
            selected_index = st.selectbox(
                "削除するデータを選択してください",
                range(len(df)),
                format_func=lambda x: f"{df.iloc[x]['title']} ({df.iloc[x]['created_at']})"
            )
            
            selected_record = df.iloc[selected_index]
            
            # 削除確認
            st.write("**削除対象:**")
            st.write(f"- タイトル: {selected_record.get('title', 'N/A')}")
            st.write(f"- テキスト: {selected_record.get('text_content', 'N/A')[:100]}...")
            st.write(f"- 作成日時: {selected_record.get('created_at', 'N/A')}")
            
            if st.button("🗑️ 削除実行", type="secondary"):
                if delete_record(conn, selected_index):
                    st.success("データが削除されました！")
                    st.rerun()
                else:
                    st.error("データの削除に失敗しました。")
        else:
            st.info("削除可能なデータがありません。")
    
    elif mode == "音声生成":
        st.header("🎵 音声生成")
        
        if not tts_client:
            st.error("Text-to-Speechクライアントが利用できません。")
            return
        
        if not df.empty:
            # 音声生成対象を選択
            selected_index = st.selectbox(
                "音声生成するデータを選択してください",
                range(len(df)),
                format_func=lambda x: f"{df.iloc[x]['title']} ({df.iloc[x]['created_at']})"
            )
            
            selected_record = df.iloc[selected_index]
            
            st.write("**選択されたデータ:**")
            st.write(f"- タイトル: {selected_record.get('title', 'N/A')}")
            st.write(f"- 言語: {selected_record.get('language', 'N/A')}")
            st.write(f"- 音声: {selected_record.get('voice', 'N/A')}")
            
            with st.expander("テキスト内容"):
                st.write(selected_record.get('text_content', 'N/A'))
            
            if st.button("🎵 音声生成", type="primary"):
                with st.spinner("音声を生成中..."):
                    audio_content = generate_speech(
                        tts_client,
                        selected_record.get('text_content', ''),
                        selected_record.get('language', 'ja-JP'),
                        selected_record.get('voice', 'ja-JP-Wavenet-A')
                    )
                    
                    if audio_content:
                        st.success("音声が生成されました！")
                        
                        # 音声プレイヤー
                        st.audio(audio_content, format='audio/mp3')
                        
                        # ダウンロードボタン
                        st.download_button(
                            label="🔽 音声ファイルをダウンロード",
                            data=audio_content,
                            file_name=f"{selected_record.get('title', 'audio')}.mp3",
                            mime="audio/mp3"
                        )
                    else:
                        st.error("音声生成に失敗しました。")
        else:
            st.info("音声生成可能なデータがありません。")

if __name__ == "__main__":
    main()