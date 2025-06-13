import numpy as np
from PIL import Image
import wave
import struct
import os
import json
import base64

def hide_text(carrier_path, output_path, secret_text, carrier_type):
    """将文本隐藏到载体文件中"""
    if carrier_type == '图片':
        hide_text_in_image(carrier_path, output_path, secret_text)
    elif carrier_type == '音频':
        hide_text_in_audio(carrier_path, output_path, secret_text)
    elif carrier_type == '视频':
        # 使用PNG作为载体的视频隐写
        output_path, png_carrier_path = hide_text_in_video_using_png(carrier_path, output_path, secret_text)
        print(f"视频隐写完成，同时创建了PNG载体: {png_carrier_path}")
        print(f"提示: 从视频中提取文本时将自动使用PNG载体文件")
    else:
        raise ValueError(f"不支持的载体类型: {carrier_type}")

def hide_file(carrier_path, output_path, secret_path, carrier_type):
    """将文件隐藏到载体文件中"""
    # 读取秘密文件
    with open(secret_path, 'rb') as f:
        file_data = f.read()
    
    # 创建元数据（包含文件名和内容）
    metadata = {
        'type': 'file',
        'filename': os.path.basename(secret_path),
        'data': base64.b64encode(file_data).decode('utf-8')
    }
    
    # 将元数据转换为JSON字符串
    secret_text = json.dumps(metadata)
    
    # 使用文本隐写函数
    hide_text(carrier_path, output_path, secret_text, carrier_type)

def extract(carrier_path):
    """从载体文件中提取隐藏信息"""
    # 检测文件类型
    ext = os.path.splitext(carrier_path)[1].lower()
    
    if ext in ['.png', '.bmp', '.jpg', '.jpeg']:
        extracted_text = extract_from_image(carrier_path)
    elif ext in ['.wav']:
        extracted_text = extract_from_audio(carrier_path)
    elif ext in ['.mp4', '.avi']:
        # 对于视频文件，直接使用对应的PNG载体文件
        # 尝试多种可能的PNG载体文件路径
        possible_paths = []
        
        # 1. 基本路径 - 与视频同目录
        basic_path = os.path.splitext(carrier_path)[0] + "_carrier.png"
        possible_paths.append(basic_path)
        
        # 2. 如果路径包含uploads目录，尝试在uploads目录中查找
        if 'uploads' in carrier_path:
            uploads_dir = os.path.join(os.path.dirname(os.path.dirname(carrier_path)), 'uploads')
            basename = os.path.basename(os.path.splitext(carrier_path)[0]) + "_carrier.png"
            uploads_path = os.path.join(uploads_dir, basename)
            possible_paths.append(uploads_path)
        
        # 3. 尝试当前工作目录
        cwd_path = os.path.join(os.getcwd(), os.path.basename(os.path.splitext(carrier_path)[0]) + "_carrier.png")
        possible_paths.append(cwd_path)
        
        # 4. 尝试uploads子目录
        uploads_subdir_path = os.path.join('uploads', os.path.basename(os.path.splitext(carrier_path)[0]) + "_carrier.png")
        possible_paths.append(uploads_subdir_path)
        
        # 5. 处理中文编码问题 - 尝试查找目录中所有可能匹配的文件
        dir_path = os.path.dirname(carrier_path)
        if os.path.exists(dir_path):
            base_name = os.path.basename(os.path.splitext(carrier_path)[0])
            for file in os.listdir(dir_path):
                if file.endswith("_carrier.png"):
                    # 检查文件名是否可能是编码不一致的版本
                    possible_match = os.path.join(dir_path, file)
                    possible_paths.append(possible_match)
        
        # 6. 在uploads目录中查找所有可能匹配的文件
        uploads_dir = 'uploads'
        if os.path.exists(uploads_dir):
            for file in os.listdir(uploads_dir):
                if file.endswith("_carrier.png"):
                    possible_match = os.path.join(uploads_dir, file)
                    possible_paths.append(possible_match)
        
        # 打印所有可能的路径以便调试
        print(f"正在查找PNG载体文件，尝试以下路径:")
        for path in possible_paths:
            print(f"- {path}")
        
        # 尝试所有可能的路径
        png_carrier_path = None
        for path in possible_paths:
            if os.path.exists(path):
                png_carrier_path = path
                print(f"找到PNG载体图像: {png_carrier_path}")
                break
        
        if png_carrier_path:
            print(f"从PNG载体中提取文本...")
            extracted_text = extract_from_image(png_carrier_path)
            if extracted_text:
                print(f"成功从PNG载体中提取文本，长度: {len(extracted_text)}")
            else:
                print("从PNG载体提取失败")
                extracted_text = ""
        else:
            print("未找到任何PNG载体图像")
            print("视频隐写提取需要对应的PNG载体文件")
            extracted_text = ""
    elif ext in ['.m4a', '.mp3', '.aac']:
        # 对于不支持的音频格式，提示用户转换为WAV格式
        print("注意: 当前版本仅支持WAV格式的音频文件")
        print("请将您的音频文件转换为WAV格式后再试")
        print("您可以使用在线转换工具或音频编辑软件进行转换")
        return ""
    else:
        raise ValueError(f"不支持的文件类型: {ext}")
    
    # 尝试解析JSON
    try:
        data = json.loads(extracted_text)
        if isinstance(data, dict) and data.get('type') == 'file':
            # 这是一个文件，返回文件信息和二进制数据
            filename = data.get('filename', 'extracted_file')
            file_data = base64.b64decode(data['data'])
            return {
                'type': 'file',
                'filename': filename,
                'data': file_data
            }
        else:
            # 这是普通文本
            return {
                'type': 'text',
                'data': extracted_text
            }
    except (json.JSONDecodeError, TypeError):
        # 不是JSON格式或者是None，当作普通文本返回
        return {
            'type': 'text',
            'data': extracted_text if extracted_text else ""
        }

# 图片隐写实现
def hide_text_in_image(image_path, output_path, text):
    """在图片中隐藏文本"""
    # 将文本转换为二进制，使用UTF-8编码确保正确处理中文
    text_bytes = text.encode('utf-8')
    
    # 添加长度前缀，便于提取时知道实际数据长度
    length_bytes = len(text_bytes).to_bytes(4, byteorder='big')
    data_to_hide = length_bytes + text_bytes
    
    # 将字节转换为二进制字符串
    binary_text = ''.join(format(byte, '08b') for byte in data_to_hide)
    
    # 打开图片
    img = Image.open(image_path)
    
    # 确保图片是RGB模式
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    width, height = img.size
    
    # 检查图片容量是否足够
    if len(binary_text) > width * height * 3:
        raise ValueError("图片容量不足以隐藏所有数据")
    
    # 转换为numpy数组以便处理
    img_array = np.array(img)
    
    # 隐藏数据
    idx = 0
    for i in range(height):
        for j in range(width):
            for k in range(3):  # RGB通道
                if idx < len(binary_text):
                    # 修改最低有效位
                    img_array[i, j, k] = (img_array[i, j, k] & 0xFE) | int(binary_text[idx])
                    idx += 1
                else:
                    break
            if idx >= len(binary_text):
                break
        if idx >= len(binary_text):
            break
    
    # 保存修改后的图片 - 强制使用PNG格式
    output_img = Image.fromarray(img_array)
    
    # 强制使用PNG格式，无论用户选择什么格式
    output_path_png = os.path.splitext(output_path)[0] + '.png'
    output_img.save(output_path_png)
    print(f"成功隐藏文本，长度: {len(text)}，保存到: {output_path_png}")
    
    # 如果用户要求的不是PNG格式，提供警告
    if output_path != output_path_png:
        print(f"警告: 已将输出格式更改为PNG以确保数据不丢失。原始请求格式({os.path.splitext(output_path)[1]})会导致隐写数据丢失。")
    
    return output_path_png  # 返回实际保存的文件路径

def extract_from_image(image_path):
    """从图片中提取隐藏文本"""
    try:
        # 打开图片
        img = Image.open(image_path)
        width, height = img.size
        
        # 转换为numpy数组
        img_array = np.array(img)
        
        # 检查图片是否有alpha通道，如果有，我们只使用RGB通道
        channels = min(3, img_array.shape[2])
        
        # 提取二进制数据
        binary_data = ""
        
        # 按照与隐藏时相同的顺序提取数据
        for i in range(height):
            for j in range(width):
                for k in range(channels):  # RGB通道
                    binary_data += str(img_array[i, j, k] & 1)
        
        # 确保至少有32位用于长度信息
        if len(binary_data) < 32:
            print("图片数据不足")
            return ""
        
        # 解析长度信息
        length_bytes = bytearray()
        for b in range(0, 32, 8):
            byte = binary_data[b:b+8]
            length_bytes.append(int(byte, 2))
        
        # 将字节转换为整数
        data_length = int.from_bytes(length_bytes, byteorder='big')
        print(f"解析到的数据长度: {data_length}")
        
        # 检查数据长度是否合理
        if data_length <= 0 or data_length > 1000000:  # 设置一个合理的上限
            print(f"解析到的数据长度不合理: {data_length}")
            return ""
        
        # 计算需要提取的总位数
        total_bits_needed = 32 + (data_length * 8)
        
        # 确保有足够的数据
        if len(binary_data) < total_bits_needed:
            print(f"数据不足，需要{total_bits_needed}位，但只有{len(binary_data)}位")
            return ""
        
        # 提取实际数据
        data_binary = binary_data[32:total_bits_needed]
        byte_array = bytearray()
        for b in range(0, len(data_binary), 8):
            if b + 8 <= len(data_binary):
                byte = data_binary[b:b+8]
                byte_array.append(int(byte, 2))
        
        # 解码
        try:
            result = byte_array.decode('utf-8')
            print(f"成功提取文本，长度: {len(result)}")
            return result
        except UnicodeDecodeError:
            print("UTF-8解码失败，尝试部分解码")
            # 如果解码失败，尝试解码尽可能多的有效字节
            for i in range(len(byte_array), 0, -1):
                try:
                    result = byte_array[:i].decode('utf-8')
                    print(f"部分解码成功，长度: {len(result)}")
                    return result
                except UnicodeDecodeError:
                    continue
            print("所有解码尝试都失败")
            return ""
    except Exception as e:
        print(f"图片提取错误: {e}")
        return ""

# 音频隐写实现
def hide_text_in_audio(audio_path, output_path, text):
    """在音频中隐藏文本"""
    # 检查文件格式
    ext = os.path.splitext(audio_path)[1].lower()
    if ext != '.wav':
        raise ValueError("当前版本仅支持WAV格式的音频文件，请将您的音频文件转换为WAV格式后再试")
    
    # 将文本转换为二进制，使用UTF-8编码确保正确处理中文
    text_bytes = text.encode('utf-8')
    
    # 添加长度前缀，便于提取时知道实际数据长度
    length_bytes = len(text_bytes).to_bytes(4, byteorder='big')
    data_to_hide = length_bytes + text_bytes
    
    # 将字节转换为二进制字符串
    binary_text = ''.join(format(byte, '08b') for byte in data_to_hide)
    
    # 打开音频文件
    with wave.open(audio_path, 'rb') as wav:
        params = wav.getparams()
        frames = wav.readframes(wav.getnframes())
    
    # 检查音频容量是否足够
    if len(binary_text) > len(frames) // 2:
        raise ValueError("音频容量不足以隐藏所有数据")
    
    # 将帧数据转换为整数列表
    frame_data = list(struct.unpack(f"{len(frames)//2}h", frames))
    
    # 隐藏数据
    for i in range(len(binary_text)):
        if i < len(frame_data):
            # 修改最低有效位
            frame_data[i] = (frame_data[i] & 0xFFFE) | int(binary_text[i])
    
    # 将修改后的帧数据转换回字节
    modified_frames = struct.pack(f"{len(frame_data)}h", *frame_data)
    
    # 保存修改后的音频
    with wave.open(output_path, 'wb') as wav:
        wav.setparams(params)
        wav.writeframes(modified_frames)

def extract_from_audio(audio_path):
    """从音频中提取隐藏文本"""
    try:
        # 打开音频文件
        with wave.open(audio_path, 'rb') as wav:
            frames = wav.readframes(wav.getnframes())
        
        # 将帧数据转换为整数列表
        frame_data = list(struct.unpack(f"{len(frames)//2}h", frames))
        
        # 提取二进制数据
        binary_data = ""
        
        # 提取所有位 - 与隐藏时的逻辑完全匹配
        for i in range(len(frame_data)):
            binary_data += str(frame_data[i] & 1)
        
        # 确保至少有32位用于长度信息
        if len(binary_data) < 32:
            print("音频数据不足32位")
            return ""
        
        # 解析长度信息
        length_bytes = bytearray()
        for b in range(0, 32, 8):
            byte = binary_data[b:b+8]
            length_bytes.append(int(byte, 2))
        
        # 将字节转换为整数
        data_length = int.from_bytes(length_bytes, byteorder='big')
        print(f"解析到的数据长度: {data_length}")
        
        # 检查数据长度是否合理
        if data_length <= 0 or data_length > 1000000:  # 设置一个合理的上限
            print(f"解析到的数据长度不合理: {data_length}")
            return ""
        
        # 计算需要提取的总位数
        total_bits_needed = 32 + (data_length * 8)
        
        # 确保有足够的数据
        if len(binary_data) < total_bits_needed:
            print(f"音频数据不足，需要{total_bits_needed}位，但只有{len(binary_data)}位")
            return ""
        
        # 提取实际数据
        data_binary = binary_data[32:total_bits_needed]
        byte_array = bytearray()
        for b in range(0, len(data_binary), 8):
            if b + 8 <= len(data_binary):
                byte = data_binary[b:b+8]
                byte_array.append(int(byte, 2))
        
        # 解码
        try:
            result = byte_array.decode('utf-8')
            print(f"成功提取文本，长度: {len(result)}")
            return result
        except UnicodeDecodeError:
            print("UTF-8解码失败，尝试部分解码")
            # 如果解码失败，尝试解码尽可能多的有效字节
            for i in range(len(byte_array), 0, -1):
                try:
                    result = byte_array[:i].decode('utf-8')
                    print(f"部分解码成功，长度: {len(result)}")
                    return result
                except UnicodeDecodeError:
                    continue
            print("所有解码尝试都失败")
            return ""
    except Exception as e:
        print(f"音频提取错误: {e}")
        return ""

# 视频隐写实现
def hide_text_in_video_using_png(video_path, output_path, text):
    """使用PNG图片作为载体在视频中隐藏文本"""
    try:
        import cv2
    except ImportError:
        raise ImportError("需要安装opencv-python库来处理视频")
    
    # 打开视频
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        raise ValueError("无法打开视频文件")
    
    # 获取视频信息
    fps = video.get(cv2.CAP_PROP_FPS)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # 读取第一帧
    success, frame = video.read()
    if not success:
        raise ValueError("无法读取视频帧")
    
    # 将帧保存为临时PNG图像
    temp_frame_path = "temp_frame.png"
    cv2.imwrite(temp_frame_path, frame)
    
    # 在PNG图像中隐藏文本
    temp_output_path = "temp_output_frame.png"
    hide_text_in_image(temp_frame_path, temp_output_path, text)
    
    # 读取修改后的帧
    modified_frame = cv2.imread(temp_output_path)
    if modified_frame is None:
        raise ValueError("无法读取修改后的帧")
    
    # 创建一个PNG图像作为载体 - 确保使用绝对路径
    png_carrier_path = os.path.splitext(output_path)[0] + "_carrier.png"
    png_carrier_path = os.path.abspath(png_carrier_path)
    cv2.imwrite(png_carrier_path, modified_frame)
    
    # 同时在uploads目录中创建一个副本，以防Web应用需要
    try:
        if 'uploads' in output_path:
            uploads_dir = 'uploads'
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            uploads_png_path = os.path.join(uploads_dir, os.path.basename(os.path.splitext(output_path)[0]) + "_carrier.png")
            cv2.imwrite(uploads_png_path, modified_frame)
            print(f"已在uploads目录创建PNG载体副本: {uploads_png_path}")
    except Exception as e:
        print(f"创建uploads目录PNG载体副本时出错: {e}")
    
    print(f"已创建PNG载体图像: {png_carrier_path}")
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # 写入修改后的第一帧
    out.write(modified_frame)
    
    # 复制其余帧
    while True:
        success, frame = video.read()
        if not success:
            break
        out.write(frame)
    
    # 释放资源
    video.release()
    out.release()
    
    # 删除临时文件
    if os.path.exists(temp_frame_path):
        os.remove(temp_frame_path)
    if os.path.exists(temp_output_path):
        os.remove(temp_output_path)
    
    print(f"成功在视频中隐藏文本，长度: {len(text)}，保存到: {output_path}")
    print(f"同时创建了PNG载体图像: {png_carrier_path}")
    print(f"提示: 从视频中提取文本时将自动使用PNG载体图像")
    
    return output_path, png_carrier_path