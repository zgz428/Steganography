document.addEventListener('DOMContentLoaded', function() {
    // 标签切换
    const encodeTab = document.getElementById('encode-tab');
    const decodeTab = document.getElementById('decode-tab');
    const encodeContent = document.getElementById('encode-content');
    const decodeContent = document.getElementById('decode-content');
    
    encodeTab.addEventListener('click', function() {
        encodeTab.classList.add('active');
        decodeTab.classList.remove('active');
        encodeContent.style.display = 'block';
        decodeContent.style.display = 'none';
    });
    
    decodeTab.addEventListener('click', function() {
        decodeTab.classList.add('active');
        encodeTab.classList.remove('active');
        decodeContent.style.display = 'block';
        encodeContent.style.display = 'none';
    });
    
    // 文件选择按钮
    const fileInputs = document.querySelectorAll('input[type="file"]');
    const fileButtons = document.querySelectorAll('.file-btn');
    
    fileButtons.forEach((btn, index) => {
        btn.addEventListener('click', function() {
            fileInputs[index].click();
        });
    });
    
    fileInputs.forEach((input) => {
        input.addEventListener('change', function() {
            const fileName = this.files[0] ? this.files[0].name : '未选择文件';
            this.nextElementSibling.textContent = fileName;
        });
    });
    
    // 信息类型切换
    const secretType = document.getElementById('secret-type');
    const textInputContainer = document.getElementById('text-input-container');
    const fileInputContainer = document.getElementById('file-input-container');
    
    secretType.addEventListener('change', function() {
        if (this.value === '文本') {
            textInputContainer.style.display = 'block';
            fileInputContainer.style.display = 'none';
        } else {
            textInputContainer.style.display = 'none';
            fileInputContainer.style.display = 'block';
        }
    });
    
    // 隐藏信息
    const encodeBtn = document.getElementById('encode-btn');
    
    encodeBtn.addEventListener('click', function() {
        const carrierType = document.getElementById('carrier-type').value;
        const carrierFile = document.getElementById('carrier-file').files[0];
        const secretType = document.getElementById('secret-type').value;
        
        if (!carrierFile) {
            alert('请选择载体文件');
            return;
        }
        
        const formData = new FormData();
        formData.append('carrier_type', carrierType);
        formData.append('carrier_file', carrierFile);
        formData.append('secret_type', secretType);
        
        if (secretType === '文本') {
            const secretText = document.getElementById('secret-text').value;
            if (!secretText) {
                alert('请输入要隐藏的文本');
                return;
            }
            formData.append('secret_text', secretText);
        } else {
            const secretFile = document.getElementById('secret-file').files[0];
            if (!secretFile) {
                alert('请选择要隐藏的文件');
                return;
            }
            formData.append('secret_file', secretFile);
        }
        
        fetch('/encode', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                return response.blob();
            } else {
                return response.json().then(data => {
                    throw new Error(data.message || '隐写失败');
                });
            }
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `hidden_${carrierFile.name}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            alert('隐写成功，文件已下载');
        })
        .catch(error => {
            alert(error.message);
        });
    });
    
    // 提取信息
    const decodeBtn = document.getElementById('decode-btn');
    
    decodeBtn.addEventListener('click', function() {
        const carrierFile = document.getElementById('decode-file').files[0];
        
        if (!carrierFile) {
            alert('请选择含有隐藏信息的文件');
            return;
        }
        
        const formData = new FormData();
        formData.append('carrier_file', carrierFile);
        
        fetch('/decode', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            } else {
                return response.blob().then(blob => {
                    return { success: true, type: 'file', blob: blob };
                });
            }
        })
        .then(data => {
            if (!data.success && data.message) {
                throw new Error(data.message);
            }
            
            if (data.type === 'text') {
                // 显示提取的文本
                document.getElementById('result-text').textContent = data.data;
                document.getElementById('text-result').style.display = 'block';
                document.getElementById('file-result').style.display = 'none';
            } else if (data.type === 'file' || data.blob) {
                // 显示文件下载链接
                const blob = data.blob;
                const url = window.URL.createObjectURL(blob);
                
                document.getElementById('file-result').style.display = 'block';
                document.getElementById('text-result').style.display = 'none';
                
                const downloadLink = document.getElementById('download-link');
                downloadLink.href = url;
                downloadLink.textContent = '点击下载提取的文件';
                
                // 自动下载
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'extracted_file';
                document.body.appendChild(a);
                a.click();
                
                // 不要立即释放URL，让用户有机会点击下载链接
                setTimeout(() => {
                    window.URL.revokeObjectURL(url);
                }, 60000); // 1分钟后释放
            }
        })
        .catch(error => {
            alert(error.message);
        });
    });
});