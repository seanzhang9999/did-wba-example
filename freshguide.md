如果你是小白，可以通过如下方式从零开始运行
# Windows

# Mac
在设置Python开发环境时，通常会有一些工具需要全局安装，而其他工具则适合在项目的虚拟环境中安装。以下是一个理想的安装顺序和建议：

## 全局安装
1. pip : 通常已经随Python安装一起提供，用于安装和管理Python包。
2. pipx : 用于全局安装和管理独立的Python应用程序。适合安装像 poetry 这样的工具。
   
   ```bash
   pip install pipx
   pipx ensurepath
    ```
3. poetry : 用于依赖管理和打包的工具，建议通过 pipx 全局安装，以便在多个项目中使用。
   
   ```bash
   pipx install poetry
   pipx ensurepath
    ```
## 虚拟环境安装
1. .venv : 在项目目录下创建虚拟环境，用于隔离项目的依赖。
   
   ```bash
   python3 -m venv .venv
    ```
2. 项目依赖 : 在激活虚拟环境后，通过 poetry 安装项目的依赖。
   
   ```bash
   source .venv/bin/activate
   poetry install
    ```
3. 退出虚拟环境:

   ```bash
   deactivate
    ```
通过这种方式，你可以确保全局工具的独立性和项目依赖的隔离性，避免不同项目之间的依赖冲突。

## 运行项目 
1. 克隆项目
2. 创建环境配置文件
   ```
   cp .env.example .env
   ```
3. 编辑.env文件，设置必要的配置项
4. 启动服务器
   ```bash
   python did_server.py
   ```
5. 启动客户端
   ```bash
     # 在第二个终端窗口启动客户端，指定不同端口
   python did_server.py --client --port 8001
   ```
6. logs目录无权限
    mac下可以通过find命令查找并修改权限
    ```bash
    find logs -type d -exec chmod 777 {} \;
    find logs -type f -exec chmod 666 {} \;
    ```
