import chainlit as cl
from langchain_core.messages import HumanMessage
import os

# Import Logic từ Source
from src.services.agent import graph as agent_app 
from src.services.file_search import GeminiRAGService

# Khởi tạo service xử lý file
rag_service = GeminiRAGService()


#          uv run chainlit run app.py -w


@cl.on_chat_start
async def start():
    # Gửi lời chào mở đầu (Đã loại bỏ hết icons/emojis)
    welcome_message = """
**BKCore AI xin chào các Cổ đông và Quý bửu ưu tú của Đại học Bách Khooa Hà Nội!**

Tôi được lập trình để giúp bạn sống sót qua 5 năm đại học mà vẫn bảo toàn tính mạng và tinh thần. Dưới đây là một số tính năng nổi bật của tôi:

1. **Kim chỉ nam sinh tồn**
   Quên lịch đóng tiền? Mất thẻ BHYT? Không biết quy chế? Hỏi lẹ đi không lại "Hẹn em kỳ sau".

2. **Máy nghiền tài liệu**
   Mấy cái văn bản dài dòng văn tự, bạn cứ để lên đây. Tôi đọc hộ cho, thời gian đó để mà giải tích.

3. **Tâm sự tuổi hồng**
   Crush không rep inbox thì qua đây chat với tui. Tui hứa sẽ rep nhanh hơn người yêu cũ của bạn.

*Gõ gì đi fen, đừng để tui chờ lâu nhé!*
"""
    await cl.Message(content=welcome_message).send()
    
    # Khởi tạo lịch sử chat
    cl.user_session.set("history", [])

@cl.on_message
async def main(message: cl.Message):
    # --- 1. XỬ LÝ FILE UPLOAD (NẾU CÓ) ---
    if message.elements:
        processing_msg = cl.Message(content="Đang tiếp nhận và xử lý tài liệu...", author="System")
        await processing_msg.send()
        
        uploaded_files = []
        for element in message.elements:
            if "text" in element.mime or "pdf" in element.mime:
                try:
                    rag_service.upload_file(
                        file_path=element.path,
                        file_name=element.name,
                        store_name="rag-store"
                    )
                    uploaded_files.append(element.name)
                except Exception as e:
                    await cl.Message(content=f"Lỗi khi upload {element.name}: {e}").send()
        
        if uploaded_files:
            await processing_msg.remove()
            await cl.Message(
                content=f"Đã học xong {len(uploaded_files)} tài liệu: **{', '.join(uploaded_files)}**.\nGiờ bạn có thể hỏi về nội dung của chúng!",
                author="BKSA"
            ).send()

    # --- 2. XỬ LÝ CHAT VỚI AGENT ---
    if not message.content and message.elements:
        return

    msg = cl.Message(content="")
    await msg.send()
    
    try:
        inputs = {"messages": [HumanMessage(content=message.content)]}
        result = await agent_app.ainvoke(inputs, config={"recursion_limit": 15})
        
        last_msg = result["messages"][-1]
        response_text = last_msg.content
        bot_name = last_msg.name if hasattr(last_msg, "name") else "BKSA"
        
        # Đổi tên Bot hiển thị cho thân thiện (ĐÃ BỎ ICONS)
        name_display = {
            "Domain_Bot": "Tư vấn HUST",
            "File_Bot": "Trợ lý Tài liệu",
            "General_Bot": "BKSA",
            "RAG_Agent": "Bot Tra cứu"
        }.get(bot_name, "BKSA")

        # Hiển thị ra màn hình
        msg.content = response_text
        msg.author = name_display
        await msg.update()
        
    except Exception as e:
        msg.content = f"Hệ thống gặp sự cố: {str(e)}"
        await msg.update()