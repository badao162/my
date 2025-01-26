import tkinter as tk
from PIL import ImageGrab
import easyocr
import pyautogui
import numpy as np
from transformers import pipeline
import threading

# 全局变量
start_x = start_y = end_x = end_y = 0
rect_id = None  # 用于存储选择框的 ID
root = None
canvas = None

# 新窗口用于显示提取的文字和翻译结果
result_window = None
extracted_text_widget = None
translated_text_widget = None


def on_mouse_down(event):
    global start_x, start_y
    start_x, start_y = event.x, event.y  # 记录起始点


def on_mouse_move(event):
    global rect_id, canvas
    end_x, end_y = event.x, event.y  # 更新终点坐标

    # 删除旧的选择框并绘制新的
    if rect_id:
        canvas.delete(rect_id)
    rect_id = canvas.create_rectangle(
        start_x, start_y, end_x, end_y,
        outline="red", width=2, dash=(4, 2)
    )


def on_mouse_up(event):
    global end_x, end_y, root
    end_x, end_y = event.x, event.y  # 记录终点
    if root:  # 销毁窗口以退出全屏模式
        root.destroy()


def screenshot():
    global root, canvas, start_x, start_y, end_x, end_y

    # 获取屏幕分辨率
    screen_width, screen_height = pyautogui.size()

    # 创建全屏透明窗口
    root = tk.Tk()
    root.attributes("-fullscreen", True)  # 全屏模式
    root.attributes("-alpha", 0.3)  # 半透明
    root.configure(bg="black")

    # 创建画布，用于绘制选择框
    canvas = tk.Canvas(root, width=screen_width, height=screen_height, bg="black")
    canvas.pack(fill=tk.BOTH, expand=True)

    # 绑定鼠标事件
    canvas.bind("<Button-1>", on_mouse_down)  # 鼠标按下
    canvas.bind("<B1-Motion>", on_mouse_move)  # 鼠标移动
    canvas.bind("<ButtonRelease-1>", on_mouse_up)  # 鼠标释放

    root.mainloop()  # 事件循环

    # 确保坐标从左上到右下，并限制在屏幕范围内
    x1, y1 = max(0, min(start_x, end_x)), max(0, min(start_y, end_y))
    x2, y2 = min(screen_width, max(start_x, end_x)), min(screen_height, max(start_y, end_y))

    # 截取屏幕
    print(f"截图区域: ({x1}, {y1}, {x2}, {y2})")  # 调试用
    screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    return screenshot


def extract_text(image):
    # 使用 easyocr 提取文字
    reader = easyocr.Reader(['en', 'ch_sim'], gpu=True)  # 加载英语和中文模型

    # 将 PIL.Image 转换为 NumPy 数组
    image_np = np.array(image)

    # 提取图片中的文字
    result = reader.readtext(image_np)

    # 输出提取的文字
    extracted_text = ""
    for detection in result:
        extracted_text += detection[1] + "\n"  # detection[1] 是提取的文本内容
    return extracted_text


def translate_text(text, target_language="en"):
    # 使用 transformers 提供的翻译模型
    translator = pipeline("translation", model=f"Helsinki-NLP/opus-mt-en-zh")  # 从英文翻译为中文
    translations = translator(text)
    return translations[0]['translation_text']


def update_result_window(extracted_text, translated_text):
    """更新新窗口中的提取文本和翻译结果"""
    if result_window:
        extracted_text_widget.delete(1.0, tk.END)  # 清空当前提取文本
        extracted_text_widget.insert(tk.END, extracted_text)

        translated_text_widget.delete(1.0, tk.END)  # 清空当前翻译结果
        translated_text_widget.insert(tk.END, translated_text)


def on_click_capture():
    print("请拖动鼠标选择截图区域...")

    # 1. 截取屏幕区域
    img = screenshot()
    # img.show()  # 显示截图，供用户确认

    # 2. 提取文字
    print("正在提取文字...")
    extracted_text = extract_text(img)
    print("\n提取的文字：")
    print(extracted_text)

    # 3. 翻译文字
    print("\n正在翻译...")
    translated_text = translate_text(extracted_text, target_language="en")
    print("翻译结果：")
    print(translated_text)

    # 更新结果窗口
    update_result_window(extracted_text, translated_text)

    # 提示用户继续点击
    root.after(1000, on_click_capture)


def start_capture_in_thread():
    capture_thread = threading.Thread(target=on_click_capture)
    capture_thread.daemon = True  # 使线程在主程序退出时自动结束
    capture_thread.start()


def open_result_window():
    """打开一个新窗口来显示提取的文字和翻译结果，并使其紧贴主窗口"""
    global result_window, extracted_text_widget, translated_text_widget
    result_window = tk.Toplevel()
    result_window.title("提取文字与翻译结果")

    # 设置新窗口大小
    result_window.geometry("600x400")

    # 创建框架用于文本框的排版
    frame = tk.Frame(result_window)
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    # 创建两个文本框，分别用于显示提取的文字和翻译结果
    extracted_text_widget = tk.Text(frame, wrap=tk.WORD, width=70, height=10, font=("Arial", 12), bg="#f0f0f0", bd=2, relief="groove")
    extracted_text_widget.pack(padx=20, pady=10)
    extracted_text_widget.insert(tk.END, "等待截图并提取文字...\n")

    translated_text_widget = tk.Text(frame, wrap=tk.WORD, width=70, height=10, font=("Arial", 12), bg="#f0f0f0", bd=2, relief="groove")
    translated_text_widget.pack(padx=20, pady=10)
    translated_text_widget.insert(tk.END, "等待翻译...\n")


def update_main_window_position():
    """更新主窗口位置，使其与副窗口同步移动"""
    main_window_x = result_window.winfo_x()
    main_window_y = result_window.winfo_y() + result_window.winfo_height()

    # 更新主窗口位置
    root.geometry(f"200x100+{main_window_x}+{main_window_y}")

    # 每100毫秒更新一次主窗口位置
    root.after(100, update_main_window_position)


def open_main_window():
    """打开主窗口并调整按钮位置"""
    global root
    root = tk.Tk()
    root.title("截图并翻译")

    # 设置主窗口样式
    root.geometry("200x100")
    root.configure(bg="#f5f5f5")
    root.resizable(False, False)

    # 创建按钮
    button = tk.Button(root, text="开始截图并翻译", command=start_capture_in_thread, font=("Arial", 14), bg="#4CAF50", fg="white", bd=0, relief="raised")
    button.pack(pady=20, padx=20)

    # 打开结果窗口
    open_result_window()

    # 启动定时更新主窗口位置的函数
    update_main_window_position()

    root.mainloop()


if __name__ == "__main__":
    open_main_window()
