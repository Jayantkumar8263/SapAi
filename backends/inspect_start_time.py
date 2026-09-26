import win32com.client

sap = win32com.client.GetObject("SAPGUI")
app = sap.GetScriptingEngine
session = app.Children(0).Children(0)

root = session.FindById("wnd[1]/usr")

print("WINDOW:", session.FindById("wnd[1]").Text)
print("ROOT:", root.Id)

def walk(control, level=0):
    try:
        count = control.Children.Count
    except Exception:
        return

    for i in range(count):
        try:
            child = control.Children(i)

            print(
                "  " * level,
                i,
                child.Id,
                "|",
                getattr(child, "Type", ""),
                "|",
                getattr(child, "Name", ""),
                "|",
                repr(getattr(child, "Text", "")),
                "|",
                getattr(child, "Tooltip", "")
            )

            walk(child, level + 1)

        except Exception as e:
            print("  " * level, "ERROR:", i, e)

walk(root)
