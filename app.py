import streamlit as st
import pandas as pd
import uuid
from streamlit_gsheets import GSheetsConnection

# --- 画面のタイトルを設定 ---
st.set_page_config(page_title="データ管理アプリ (スプシ版)", layout="wide")
st.title("📋 データ管理アプリ (スプレッドシート連携版)")
st.caption("データはGoogleスプレッドシートに永続的に保存されます。")

# --- Googleスプレッドシートへの接続を確立 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- データ読み込み/書き込み関数 (スプシ版) ---
def load_data(worksheet_name="シート1"):
    try:
        sheet = conn.read(worksheet=worksheet_name, ttl=5)
        return sheet.to_dict('records')
    except Exception as e:
        st.error(f"スプレッドシートの読み込みに失敗しました: {e}")
        return []

def save_data(worksheet_name="シート1"):
    """session_stateのデータをGoogleスプレッドシートに保存"""
    try:
        if st.session_state.data:
            # session_stateのデータをDataFrameに変換
            df = pd.DataFrame(st.session_state.data)
            
            # スプレッドシートに書き込み
            conn.clear(worksheet=worksheet_name)
            conn.update(worksheet=worksheet_name, data=df)
        else:
            # データが空の場合はシートをクリア
            conn.clear(worksheet=worksheet_name)
    except Exception as e:
        st.error(f"スプレッドシートへの書き込みに失敗しました: {e}")

# --- st.session_stateの初期化 ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# 以下、UIや状態管理のコードを追加...
if 'page' not in st.session_state:
    st.session_state.page = "一覧"
if 'edit_item' not in st.session_state:
    st.session_state.edit_item = None
if 'delete_confirm_id' not in st.session_state:
    st.session_state.delete_confirm_id = None

# --- 削除確認エリアの表示ロジック ---
if st.session_state.delete_confirm_id:
    item_to_delete = next((item for item in st.session_state.data if item['id'] == st.session_state.delete_confirm_id), None)
    if item_to_delete:
        with st.container(border=True):
            st.warning(f"**「{item_to_delete['name']}」** さんのデータを本当に削除しますか？")
            col1, col2, _ = st.columns([1, 1, 4])
            with col1:
                if st.button("はい、削除します", type="primary", use_container_width=True):
                    st.session_state.data = [d for d in st.session_state.data if d['id'] != st.session_state.delete_confirm_id]
                    save_data()  # 修正：引数なしで呼び出し
                    st.session_state.delete_confirm_id = None
                    st.toast("データを削除しました。")
                    st.rerun()
            with col2:
                if st.button("いいえ", use_container_width=True):
                    st.session_state.delete_confirm_id = None
                    st.rerun()

# --- サイドバー ---
st.sidebar.title("メニュー")
if st.sidebar.button("データ一覧", use_container_width=True):
    st.session_state.page = "一覧"
    st.session_state.edit_item = None
if st.sidebar.button("新規登録", use_container_width=True):
    st.session_state.page = "フォーム"
    st.session_state.edit_item = None

# --- メイン画面の表示を切り替え ---

# ===== 1. 一覧画面 =====
if st.session_state.page == "一覧":
    st.header("データ一覧")

    if not st.session_state.data:
        st.info("データがありません。サイドバーから新規登録してください。")
    else:
        cols = st.columns((2, 1, 3, 2))
        headers = ["名前", "年齢", "メールアドレス", "操作"]
        for col, header in zip(cols, headers):
            col.write(f"**{header}**")
        st.divider()

        for item in st.session_state.data:
            cols = st.columns((2, 1, 3, 2))
            cols[0].write(item["name"])
            cols[1].write(item["age"])
            cols[2].write(item["email"])
            
            with cols[3]:
                sub_cols = st.columns(2)
                with sub_cols[0]:
                    if st.button("✏️", key=f"edit_{item['id']}", help="編集", use_container_width=True):
                        st.session_state.edit_item = item
                        st.session_state.page = "フォーム"
                        st.rerun()
                with sub_cols[1]:
                    if st.button("🗑️", key=f"delete_{item['id']}", help="削除", use_container_width=True):
                        st.session_state.delete_confirm_id = item['id']
                        st.rerun()

# ===== 2. 入力・編集フォーム画面 =====
elif st.session_state.page == "フォーム":
    if st.session_state.edit_item:
        st.header("データ編集")
        default_item = st.session_state.edit_item
    else:
        st.header("新規登録")
        default_item = {"name": "", "age": None, "email": ""}

    with st.form("entry_form"):
        name = st.text_input("名前", value=default_item.get("name", ""))
        age = st.number_input("年齢", min_value=0, max_value=120, value=default_item.get("age"), placeholder="年齢を入力...")
        email = st.text_input("メールアドレス", value=default_item.get("email", ""))
        submitted = st.form_submit_button("確認画面へ")

        if submitted:
            if not name or not email or "@" not in email:
                st.error("名前と正しい形式のメールアドレスを入力してください。")
            else:
                st.session_state.confirm_data = {"name": name, "age": age, "email": email}
                st.session_state.page = "確認"
                st.rerun()

# ===== 3. 確認画面 =====
elif st.session_state.page == "確認":
    st.header("入力内容の確認")
    confirm_data = st.session_state.get("confirm_data", {})
    st.write(f"**名前:** {confirm_data.get('name')}")
    st.write(f"**年齢:** {confirm_data.get('age')}")
    st.write(f"**メールアドレス:** {confirm_data.get('email')}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("修正する", use_container_width=True):
            st.session_state.page = "フォーム"
            if st.session_state.edit_item:
                st.session_state.edit_item = {**st.session_state.edit_item, **confirm_data}
            else:
                st.session_state.edit_item = confirm_data
            st.rerun()
    with col2:
        if st.button("この内容で確定する", type="primary", use_container_width=True):
            if st.session_state.edit_item and 'id' in st.session_state.edit_item:
                # 編集の場合：データを更新してから保存
                st.session_state.data = [
                    {**item, **confirm_data} if item['id'] == st.session_state.edit_item['id'] else item
                    for item in st.session_state.data
                ]
                save_data()  # 修正：引数なしで呼び出し
                st.success("データを更新しました！")
            else:
                # 新規登録の場合：データを追加してから保存
                new_data = {"id": str(uuid.uuid4()), **confirm_data}
                st.session_state.data.append(new_data)
                save_data()  # 修正：引数なしで呼び出し
                st.success("データを登録しました！")

            st.session_state.page = "一覧"
            st.session_state.edit_item = None
            st.session_state.confirm_data = None
            st.balloons()
            st.rerun()