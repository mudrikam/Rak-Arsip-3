def show_statusbar_message(widget, message, timeout=2000):
    main_window = widget.window()
    if hasattr(main_window, "statusBar"):
        statusbar = main_window.statusBar()
        if statusbar:
            statusbar.showMessage(message, timeout)
