from google_auth_oauthlib.flow import InstalledAppFlow
from app.core import settings


def auth_manual():
    print(f"--- Генерация токена в {settings.TOKEN_FILE} ---")

    settings.TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not settings.CREDENTIALS_FILE.exists():
        print(f"Ошибка: Файл {settings.CREDENTIALS_FILE} не найден!")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        str(settings.CREDENTIALS_FILE), settings.SCOPES
    )

    creds = flow.run_local_server(port=0)

    with settings.TOKEN_FILE.open('w') as token:
        token.write(creds.to_json())

    print(f"Успешно! Токен сохранен.")


if __name__ == "__main__":
    auth_manual()
