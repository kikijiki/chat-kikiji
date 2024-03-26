import pyautogui
import pygetwindow as gw
import pytesseract
import pyperclip
import cv2
import numpy as np
import openai


LANGUAGE = "italian"
LANG_CODE = "ita"
AGENT_NAME = ""


openai.api_key = "sk-YOURKEYHERE"
pytesseract.pytesseract.tesseract_cmd = (
    "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
)


def get_line_window():
    return next(
        filter(lambda window: window.title == "LINE", gw.getWindowsWithTitle("LINE"))
    )


def get_line_bounds(window):
    return (window.left, window.top, window.width, window.height)


def get_line_chat_bounds(window):
    # Assuming left column is set to the minimum width
    return (
        window.left + 360,
        window.top + 100,
        window.width - 360,
        window.height - 225,
    )


def get_line_input_center(window):
    return (window.left + (2 * window.width) / 3, window.bottom - 50)


def get_screenshot(region):
    screenshot = pyautogui.screenshot(region=region)
    opencv_image = np.array(screenshot)
    opencv_image = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2BGR)
    return opencv_image


def focus_line_input(window):
    try:
        window.activate()
    except Exception as e:
        print(e)

    pyautogui.sleep(1)
    center = get_line_input_center(window)
    pyautogui.moveTo(*center)
    pyautogui.click()


def send_message(window, message):
    pyperclip.copy(message)
    focus_line_input(window)
    pyautogui.hotkey("ctrl", "v")
    #pyautogui.write(message)
    #pyautogui.press('enter')


def read_chat(image):
    # Assuming dark mode
    color_others = np.array([85, 85, 85])
    color_me = np.array([123, 217, 134])
    margin = np.array([5, 5, 5])

    mask_others = cv2.inRange(image, color_others - margin, color_others + margin)
    mask_me = cv2.inRange(image, color_me - margin, color_me + margin)

    contours_others, _ = cv2.findContours(mask_others, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours_me, _ = cv2.findContours(mask_me, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [(contour, False) for contour in contours_others] + [(contour, True) for contour in contours_me]
    contours = sorted(contours, key=lambda c: cv2.boundingRect(c[0])[1])

    lines = []
    is_last_me = False
    for contour, is_me in contours:
        x, y, w, h = cv2.boundingRect(contour)

        if w < 10 or h < 10:
            continue

        cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)

        cropped = image[y : y + h, x : x + w]
        cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)

        line = pytesseract.image_to_string(cropped_rgb)  # , lang=LANG_CODE)

        if line is None:
            continue

        line = line.strip()
        if line != "":
            speaker = "me" if is_me else "others"
            print(f"Read line from {speaker}: {line}")
            lines.append(f"- [{speaker}]: {line}")
            is_last_me = is_me

    #cv2.imwrite("screenshot.png", image)
    #cv2.imshow('Result', image)
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()

    return "\n".join(lines), is_last_me


def reply(window, message_log):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": f"""
                    Your name is {AGENT_NAME}.
                    TODO: DESCRIBE THE SCENARIO
                    """,
            },
            {
                "role": "user",
                "content": f"""
                    This is the chat history so far:

                    ```
                    {message_log}
                    ```
                    
                    Your messages start with '[me]', while the others' messages start with '[others]'.
                    There might be some errors in the transcription, ignore any line that is not intelligible.
                    Write one reply in {LANGUAGE} to continue the ongoing discussion, as if you were {AGENT_NAME}.
                    It should be under 100 words.
                    Don't be pandering.
                    Sometimes end the sentences with an emoji.
                    Don't write '- [me]' or '- [others]' in your reply, and don't start with a '- '.
                    Don't reply to your own messages (the ones that start with '- [me]' from {AGENT_NAME}).
                    Only write as {AGENT_NAME}, don't write as the other people in the chat.
                    You don't need to identify yourself, stay in character.
                    Your reply should be relevant to the current topic.
                    
                    TODO: ADD MORE CONTEXT
                """,
            },
        ],
        max_tokens=120,
        top_p=0.6,
    )

    reply = response.choices[0].message.content.strip()
    print(f"Reply: {reply}")

    send_message(window, reply)

def main():
    while True:
        window = get_line_window()
        if window is None:
            print("LINE is not running")
            continue

        try:
            window.activate()
        except Exception as e:
            print(e)

        line_bounds = get_line_chat_bounds(window)
        if line_bounds is None:
            print("LINE is not running")
            continue

        screenshot = get_screenshot(line_bounds)
        message_log, is_last_me = read_chat(screenshot)

        if not is_last_me:
            try:
                print("Replying...")
                reply(window, message_log)
            except Exception as e:
                print(e)
        else:
            print("Waiting for others to reply...")
        
        pyautogui.sleep(30)


if __name__ == "__main__":
    main()
