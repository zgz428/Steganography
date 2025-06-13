from flask import Flask, render_template, request, send_file, jsonify
import os
import steganography
import tempfile
import shutil

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 限制

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/encode', methods=['POST'])
def encode():
    # 获取载体文件类型
    carrier_type = request.form.get('carrier_type')
    
    # 获取载体文件
    carrier_file = request.files.get('carrier_file')
    if not carrier_file:
        return jsonify({'success': False, 'message': '请上传载体文件'})
    
    # 获取秘密信息类型
    secret_type = request.form.get('secret_type')
    
    # 临时保存载体文件
    carrier_path = os.path.join(app.config['UPLOAD_FOLDER'], carrier_file.filename)
    carrier_file.save(carrier_path)
    
    # 处理秘密信息
    if secret_type == '文本':
        secret_text = request.form.get('secret_text')
        if not secret_text:
            return jsonify({'success': False, 'message': '请输入要隐藏的文本'})
        
        # 生成输出文件名
        output_filename = f"hidden_{carrier_file.filename}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # 执行隐写
        try:
            steganography.hide_text(carrier_path, output_path, secret_text, carrier_type)
            return send_file(output_path, as_attachment=True, download_name=output_filename)
        except Exception as e:
            return jsonify({'success': False, 'message': f'隐写失败: {str(e)}'})
    else:  # 文件类型
        secret_file = request.files.get('secret_file')
        if not secret_file:
            return jsonify({'success': False, 'message': '请上传要隐藏的文件'})
        
        # 临时保存秘密文件
        secret_path = os.path.join(app.config['UPLOAD_FOLDER'], secret_file.filename)
        secret_file.save(secret_path)
        
        # 生成输出文件名
        output_filename = f"hidden_{carrier_file.filename}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # 执行隐写
        try:
            steganography.hide_file(carrier_path, output_path, secret_path, carrier_type)
            return send_file(output_path, as_attachment=True, download_name=output_filename)
        except Exception as e:
            return jsonify({'success': False, 'message': f'隐写失败: {str(e)}'})

@app.route('/decode', methods=['POST'])
def decode():
    # 获取载体文件
    if 'carrier_file' not in request.files:
        return jsonify({'success': False, 'message': '未上传载体文件'})
    
    carrier_file = request.files['carrier_file']
    if carrier_file.filename == '':
        return jsonify({'success': False, 'message': '未选择载体文件'})
    
    # 保存载体文件
    carrier_path = os.path.join(app.config['UPLOAD_FOLDER'], carrier_file.filename)
    carrier_file.save(carrier_path)
    
    try:
        # 提取隐藏信息
        result = steganography.extract(carrier_path)
        
        # 根据结果类型返回不同的响应
        if isinstance(result, dict):
            if result['type'] == 'file':
                # 创建临时文件
                temp_dir = tempfile.mkdtemp()
                filename = result.get('filename', 'extracted_file')
                temp_file_path = os.path.join(temp_dir, filename)
                
                # 保存提取的文件
                with open(temp_file_path, 'wb') as f:
                    f.write(result['data'])
                
                # 返回文件下载
                response = send_file(
                    temp_file_path,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/octet-stream'
                )
                
                # 设置回调以在请求完成后删除临时文件
                @response.call_on_close
                def cleanup():
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        print(f"清理临时文件时出错: {e}")
                
                return response
            else:  # 文本类型
                return jsonify({
                    'success': True,
                    'type': 'text',
                    'data': result['data']
                })
        else:
            # 兼容旧版本的返回格式
            return jsonify({
                'success': True,
                'type': 'text',
                'data': result
            })
    except Exception as e:
        return jsonify({'success': False, 'message': f'提取失败: {str(e)}'})

# 清理临时文件
@app.after_request
def cleanup(response):
    # 这里可以添加定期清理上传文件夹的逻辑
    return response

if __name__ == '__main__':
    app.run(debug=True)