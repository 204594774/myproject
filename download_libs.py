import os
import urllib.request
import ssl

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Create directory
base_dir = os.path.join(os.path.dirname(__file__), 'static', 'lib')
if not os.path.exists(base_dir):
    os.makedirs(base_dir)

# Define libraries to download
libs = [
    {
        'url': 'https://registry.npmmirror.com/vue/3.3.4/files/dist/vue.global.js',
        'filename': 'vue.global.js'
    },
    {
        'url': 'https://registry.npmmirror.com/vue-router/4.2.4/files/dist/vue-router.global.js',
        'filename': 'vue-router.global.js'
    },
    {
        'url': 'https://registry.npmmirror.com/element-plus/2.3.9/files/dist/index.css',
        'filename': 'element-plus.index.css'
    },
    {
        'url': 'https://registry.npmmirror.com/element-plus/2.3.9/files/dist/index.full.min.js',
        'filename': 'element-plus.index.full.min.js'
    },
    {
        'url': 'https://registry.npmmirror.com/@element-plus/icons-vue/2.1.0/files/dist/index.iife.min.js',
        'filename': 'element-plus-icons.index.iife.min.js'
    },
    {
        'url': 'https://registry.npmmirror.com/axios/1.4.0/files/dist/axios.min.js',
        'filename': 'axios.min.js'
    },
    {
        'url': 'https://registry.npmmirror.com/echarts/5.4.3/files/dist/echarts.min.js',
        'filename': 'echarts.min.js'
    }
]

print(f"Downloading libraries to {base_dir}...")

for lib in libs:
    try:
        url = lib['url']
        filepath = os.path.join(base_dir, lib['filename'])
        print(f"Downloading {lib['filename']}...")
        with urllib.request.urlopen(url, context=ctx) as response, open(filepath, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        print(f"Successfully downloaded {lib['filename']}")
    except Exception as e:
        print(f"Failed to download {lib['filename']}: {e}")
