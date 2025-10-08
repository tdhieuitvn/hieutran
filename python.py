# python.py

import streamlit as st
import pandas as pd
from google import genai
from google.genai.errors import APIError


import google.generativeai as genai
from google.api_core import exceptions

# --- Cấu hình Trang Streamlit ---
st.set_page_config(
    page_title="App Phân Tích Báo Cáo Tài Chính",
    page_icon="📊",
    layout="wide"
)

st.title("Ứng dụng Phân Tích Báo Cáo Tài Chính 📊")
st.caption("Tải lên file BCTC của bạn, xem phân tích và hỏi đáp trực tiếp với Gemini AI.")


# --- Hàm tính toán chính (Sử dụng Caching để Tối ưu hiệu suất) ---
@st.cache_data
def process_financial_data(df):
    """Thực hiện các phép tính Tăng trưởng và Tỷ trọng."""
    
    # Đảm bảo các giá trị là số để tính toán
    numeric_cols = ['Năm trước', 'Năm sau']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 1. Tính Tốc độ Tăng trưởng
    df['Tốc độ tăng trưởng (%)'] = (
        (df['Năm sau'] - df['Năm trước']) / df['Năm trước'].replace(0, 1e-9)
    ) * 100

    # 2. Tính Tỷ trọng theo Tổng Tài sản
    tong_tai_san_row = df[df['Chỉ tiêu'].str.contains('TỔNG CỘNG TÀI SẢN', case=False, na=False)]
    
    if tong_tai_san_row.empty:
        raise ValueError("Không tìm thấy chỉ tiêu 'TỔNG CỘNG TÀI SẢN'. Vui lòng kiểm tra lại file Excel.")

    tong_tai_san_N_1 = tong_tai_san_row['Năm trước'].iloc[0]
    tong_tai_san_N = tong_tai_san_row['Năm sau'].iloc[0]

    divisor_N_1 = tong_tai_san_N_1 if tong_tai_san_N_1 != 0 else 1e-9
    divisor_N = tong_tai_san_N if tong_tai_san_N != 0 else 1e-9

    df['Tỷ trọng Năm trước (%)'] = (df['Năm trước'] / divisor_N_1) * 100
    df['Tỷ trọng Năm sau (%)'] = (df['Năm sau'] / divisor_N) * 100
    
    return df

# --- Hàm gọi API Gemini để lấy phân tích tổng quan ---
def get_ai_summary(data_for_ai, api_key):
    """Gửi dữ liệu đã xử lý đến Gemini API và nhận lại một bài phân tích tổng quan."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        prompt = f"""
        Bạn là một chuyên gia phân tích tài chính chuyên nghiệp. Dựa trên các chỉ số tài chính sau, hãy đưa ra một nhận xét khách quan, ngắn gọn (khoảng 3-4 đoạn) về tình hình tài chính của doanh nghiệp. Đánh giá tập trung vào tốc độ tăng trưởng, thay đổi cơ cấu tài sản và khả năng thanh toán hiện hành.
        
        Dữ liệu thô và chỉ số:
        {data_for_ai}
        """

        response = model.generate_content(prompt)
        return response.text

    except exceptions.GoogleAPICallError as e:
        return f"Lỗi gọi Gemini API: Vui lòng kiểm tra lại Khóa API hoặc giới hạn sử dụng. Chi tiết lỗi: {e}"
    except Exception as e:
        return f"Đã xảy ra lỗi không xác định khi tạo phân tích: {e}"

# --- Hàm gọi API Gemini cho khung Chat ---
def ask_gemini_chat(question, context_data, api_key):
    """Gửi câu hỏi của người dùng và dữ liệu ngữ cảnh đến Gemini để nhận câu trả lời."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        prompt = f"""
        Bạn là một trợ lý AI chuyên về phân tích tài chính. Dựa vào dữ liệu báo cáo tài chính được cung cấp dưới đây, hãy trả lời câu hỏi của người dùng một cách chính xác và súc tích.

        **Dữ liệu Báo cáo tài chính:**
        {context_data}

        ---
        **Câu hỏi của người dùng:**
        {question}
        """
        response = model.generate_content(prompt)
        return response.text

    except exceptions.GoogleAPICallError as e:
        return f"Lỗi gọi Gemini API: Vui lòng kiểm tra lại Khóa API hoặc giới hạn sử dụng. Chi tiết lỗi: {e}"
    except Exception as e:
        return f"Đã xảy ra lỗi không xác định khi chat: {e}"


# --- Giao diện chính của ứng dụng ---

# --- Chức năng 1: Tải File ---
with st.sidebar:
    st.header("1. Tải File Lên")
    uploaded_file = st.file_uploader(
        "Tải file Excel Báo cáo Tài chính (Chỉ tiêu | Năm trước | Năm sau)",
        type=['xlsx', 'xls']
    )
    st.info("💡 Mẹo: Đảm bảo file Excel của bạn có 3 cột theo đúng thứ tự: 'Chỉ tiêu', 'Năm trước', 'Năm sau'.")


if uploaded_file is not None:
    try:
        df_raw = pd.read_excel(uploaded_file)
        
        # Tiền xử lý: Đảm bảo chỉ có 3 cột quan trọng
        df_raw.columns = ['Chỉ tiêu', 'Năm trước', 'Năm sau']
        
        # Xử lý dữ liệu
        df_processed = process_financial_data(df_raw.copy())

        if df_processed is not None:
            # Tách các chức năng vào các tab để giao diện gọn gàng hơn
            tab1, tab2, tab3 = st.tabs(["📊 Phân Tích Chi Tiết", "🤖 Nhận Xét từ AI", "💬 Hỏi Đáp Cùng AI"])

            with tab1:
                # --- Chức năng 2 & 3: Hiển thị Kết quả ---
                st.subheader("2. Tốc độ Tăng trưởng & 3. Tỷ trọng Cơ cấu Tài sản")
                st.dataframe(df_processed.style.format({
                    'Năm trước': '{:,.0f}',
                    'Năm sau': '{:,.0f}',
                    'Tốc độ tăng trưởng (%)': '{:.2f}%',
                    'Tỷ trọng Năm trước (%)': '{:.2f}%',
                    'Tỷ trọng Năm sau (%)': '{:.2f}%'
                }), use_container_width=True, height=500)
                
                # --- Chức năng 4: Tính Chỉ số Tài chính ---
                st.subheader("4. Các Chỉ số Tài chính Cơ bản")
                
                try:
                    # Lọc giá trị cho Chỉ số Thanh toán Hiện hành
                    tsnh_n = df_processed[df_processed['Chỉ tiêu'].str.contains('TÀI SẢN NGẮN HẠN', case=False, na=False)]['Năm sau'].iloc[0]
                    tsnh_n_1 = df_processed[df_processed['Chỉ tiêu'].str.contains('TÀI SẢN NGẮN HẠN', case=False, na=False)]['Năm trước'].iloc[0]
                    no_ngan_han_N = df_processed[df_processed['Chỉ tiêu'].str.contains('NỢ NGẮN HẠN', case=False, na=False)]['Năm sau'].iloc[0]  
                    no_ngan_han_N_1 = df_processed[df_processed['Chỉ tiêu'].str.contains('NỢ NGẮN HẠN', case=False, na=False)]['Năm trước'].iloc[0]

                    # Tính toán
                    thanh_toan_hien_hanh_N = tsnh_n / no_ngan_han_N if no_ngan_han_N != 0 else 0
                    thanh_toan_hien_hanh_N_1 = tsnh_n_1 / no_ngan_han_N_1 if no_ngan_han_N_1 != 0 else 0
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            label="Chỉ số Thanh toán Hiện hành (Năm trước)",
                            value=f"{thanh_toan_hien_hanh_N_1:.2f} lần"
                        )
                    with col2:
                        st.metric(
                            label="Chỉ số Thanh toán Hiện hành (Năm sau)",
                            value=f"{thanh_toan_hien_hanh_N:.2f} lần",
                            delta=f"{thanh_toan_hien_hanh_N - thanh_toan_hien_hanh_N_1:.2f}"
                        )
                        
                except (IndexError, KeyError):
                    st.warning("Thiếu chỉ tiêu 'TÀI SẢN NGẮN HẠN' hoặc 'NỢ NGẮN HẠN' để tính chỉ số thanh toán hiện hành.")
                    thanh_toan_hien_hanh_N = "N/A"
                    thanh_toan_hien_hanh_N_1 = "N/A"
            
            with tab2:
                # --- Chức năng 5: Nhận xét AI ---
                st.subheader("5. Nhận xét Tổng quan từ Gemini AI")
                
                if st.button("🚀 Yêu cầu AI Phân tích Tổng quan"):
                    api_key = st.secrets.get("GEMINI_API_KEY")
                    
                    if api_key:
                        with st.spinner('Đang gửi dữ liệu và chờ Gemini phân tích...'):
                            # Chuẩn bị dữ liệu để gửi cho AI
                            data_for_ai = df_processed.to_markdown(index=False)
                            ai_result = get_ai_summary(data_for_ai, api_key)
                            st.markdown("**Kết quả Phân tích từ Gemini AI:**")
                            st.info(ai_result)
                    else:
                        st.error("Lỗi: Không tìm thấy Khóa API. Vui lòng cấu hình Khóa 'GEMINI_API_KEY' trong Streamlit Secrets.")

            with tab3:
                # --- Chức năng 6: Chat với AI ---
                st.subheader("6. Hỏi đáp về Báo cáo Tài chính với Gemini AI")

                # Khởi tạo lịch sử chat
                if "messages" not in st.session_state:
                    st.session_state.messages = [{"role": "assistant", "content": "Xin chào! Dữ liệu đã sẵn sàng. Bạn muốn hỏi gì về báo cáo này?"}]

                # Hiển thị các tin nhắn đã có
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

                # Lấy input từ người dùng
                if prompt := st.chat_input("Ví dụ: 'Tài sản dài hạn thay đổi thế nào?'"):
                    api_key = st.secrets.get("GEMINI_API_KEY")
                    if not api_key:
                        st.error("Lỗi: Không tìm thấy Khóa API để bắt đầu chat. Vui lòng cấu hình 'GEMINI_API_KEY' trong Streamlit Secrets.")
                    else:
                        # Thêm tin nhắn của người dùng vào lịch sử và hiển thị
                        st.session_state.messages.append({"role": "user", "content": prompt})
                        with st.chat_message("user"):
                            st.markdown(prompt)

                        # Tạo và hiển thị phản hồi từ AI
                        with st.chat_message("assistant"):
                            with st.spinner("Gemini đang suy nghĩ..."):
                                context_for_chat = df_processed.to_markdown(index=False)
                                response = ask_gemini_chat(prompt, context_for_chat, api_key)
                                st.markdown(response)
                        
                        # Thêm phản hồi của AI vào lịch sử
                        st.session_state.messages.append({"role": "assistant", "content": response})

    except ValueError as ve:
        st.error(f"Lỗi cấu trúc dữ liệu: {ve}")
    except Exception as e:
        st.error(f"Có lỗi xảy ra khi đọc hoặc xử lý file: {e}. Vui lòng kiểm tra lại định dạng và nội dung file.")

else:
    st.info("👋 Chào mừng bạn! Vui lòng tải lên file Excel từ thanh bên để bắt đầu phân tích.")

