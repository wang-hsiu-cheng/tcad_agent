from fabric import Connection

def exec():
    try:
        with Connection("ws43") as conn:
            check_permissions(conn)
            return {"status": "success", "feedback": "Simulation finished."}
    except Exception as e:
        return {"status": "error", "feedback": str(e)}

def check_permissions(conn):
    print("--- 開始權限測試 ---")
    # 測試 1：嘗試建立一個空檔案
    res_touch = conn.run("touch test_perm.txt", warn=True)
    # 測試 2：查看當前目錄的權限
    res_ls = conn.run("ls -ld .", warn=True)
    # 測試 3：查看目前登入的使用者是誰
    res_who = conn.run("whoami", warn=True)
    if res_touch.failed:
        print(f" 權限不足：無法在該目錄建立檔案。錯誤：{res_touch.stderr}")
    else:
        print(" 權限正常：可以在該目錄建立檔案。")
        conn.run("rm test_perm.txt") # 清理測試檔
    print(f"目前目錄權限：{res_ls.stdout.strip()}")
    print(f"目前使用者：{res_who.stdout.strip()}")

if __name__ == "__main__":
    exec()