import streamlit as st

st.title("�f�o�b�O�e�X�g")

# 1. Streamlit�o�[�W�����m�F
st.write(f"Streamlit version: {st.__version__}")

# 2. st-gsheets-connection�̃C���|�[�g�e�X�g
try:
    from streamlit_gsheets import GSheetsConnection
    st.write("? GSheetsConnection �C���|�[�g����")
except ImportError as e:
    st.error(f"? GSheetsConnection �C���|�[�g���s: {e}")

# 3. st.connection�̊m�F
try:
    st.write(f"st.connection type: {type(st.connection)}")
    if hasattr(st.connection, '_REGISTRY'):
        st.write(f"_REGISTRY exists: {st.connection._REGISTRY}")
    else:
        st.write("_REGISTRY does not exist")
except Exception as e:
    st.error(f"st.connection error: {e}")

# 4. Secrets�̊m�F
try:
    if "connections" in st.secrets:
        if "gsheets" in st.secrets["connections"]:
            gsheets_info = st.secrets["connections"]["gsheets"]
            st.write(f"Secrets type: {type(gsheets_info)}")
            if hasattr(gsheets_info, '_data'):
                st.write("Has _data attribute")
            st.write(f"Keys available: {list(gsheets_info.keys()) if hasattr(gsheets_info, 'keys') else 'No keys method'}")
        else:
            st.error("gsheets not found in connections")
    else:
        st.error("connections not found in secrets")
except Exception as e:
    st.error(f"Secrets error: {e}")

# 5. �ڑ��e�X�g
try:
    if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
        conn = st.connection("gsheets", type=GSheetsConnection)
        st.write("? Connection test successful")
except Exception as e:
    st.error(f"? Connection test failed: {e}")
    st.write(f"Error type: {type(e).__name__}")