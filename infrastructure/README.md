# Инфраструктура

Этот репозиторий содержит конфигурацию инфраструктуры и средства автоматизации для управления многосерверными средами. Он создан с использованием Ansible для управления конфигурацией и следует принципам «инфраструктура как код».

## Содержание

- [Группы серверов](#Группы-серверов)
- [Требования](#Требования)
- [Начало работы](#Начало-работы)
- [Структура проекта](#Структура-проекта)
- [Available Roles](#available-roles)

## Группы серверов

Инфраструктура разделена на следующие группы серверов

| Server Group | Purpose | Admin User |
|--------------|---------|------------|
| aida | Staging/Testing environment | developer |

## Требования

- Ansible 2.9+
- Python 3.6+
- SSH access to target servers
- Переменные среды (ниже)
- Пакет sshpass при использовании пароля для доступа к серверам

## Начало работы

1. **Клонируем репозиторий**
   ```bash
   git clone <repository-url>
   cd infrastructure
   ```

2. **Устанавливаем переменные среды для доступа**
   Create a `.env` file with the following variables:
   ```
   export AIDA_USER=your_username
   export AIDA_PASS=your_password
   # Add other environment-specific variables as needed
   ```
   Then source the file:
   ```bash
   source .env
   ```

3. **Редактируем hosts файл**
   Edit `hosts.ini` with the correct IP addresses for your servers.

4. **Запускаем playbooks**

   ```bash
   ansible-playbook -i hosts.ini all.yml
   ansible-playbook -i hosts.ini all.yml --tags "docker"
   ```


## Структура проекта

```
.
├── group_vars/          # Group-specific variables
│   ├── aida/
├── roles/               # Ansible roles
│   ├── docker/
│   ├── postgres/
│   ├── migrations/
│   └── ...
├── all.yaml             # Main playbook
├── hosts.ini            # Inventory file
└── README.md            # This file
```

## Available Roles

- **docker**: Установка и настройка docker
- **postgres**: Подготовка и запуск базы данных postgres в контейнере
- **migrations**: Применение актуальных миграций
