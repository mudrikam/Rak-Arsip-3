# Rak Arsip 3 📁✨

A desktop archive management application with features for file categorization, batch tracking, client management, and wallet transactions. Built with PySide6 for cross-platform GUI support. 🎯

## Features 🚀

- **File Management** - Organize files by categories, subcategories, and statuses
- **Template System** - Create folder structure templates for organizing files
- **Batch Tracking** - Group files into batches for client projects
- **Client Management** - Manage client information and pricing
- **Wallet System** - Track pockets, cards, and financial transactions
- **Attendance** - Team check-in/check-out functionality
- **Microstock Integration** - URL-based file management with external providers
- **Migration System** - Version-controlled database schema management

## Requirements 🛠️

- Python 3.10+
- PostgreSQL 12+

## Installation 💿

```bash
git clone https://github.com/mudrikam/Rak-Arsip-3.git
cd Rak-Arsip-3
pip install -r requirements.txt
```

## Database Setup 🗄️

The application uses PostgreSQL. Create a `.env` file in the project root:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rakarsip
DB_USER=your_username
DB_PASSWORD=your_password
# DB_SSLMODE=disable  # Optional: 'disable', 'require', 'verify-full', 'prefer'
```

### Initial Setup 🔧

1. Ensure PostgreSQL is running
2. Create a database user with appropriate permissions
3. The application will automatically create the database and schema on first run (for localhost connections)

For remote PostgreSQL servers, create the database manually first:

```sql
CREATE DATABASE rakarsip;
```

## Configuration ⚙️

Application configuration files are in `configs/`:

- `db_config.json` - Database connection settings
- `window_config.json` - UI window dimensions and state
- `ai_config.json` - AI/LLM provider settings (optional)

## Running the Application ▶️

```bash
python main.py
```

## Database Schema 📊

Main tables:

| Table | Description |
|-------|-------------|
| `files` | Archived files with metadata |
| `categories` / `subcategories` | File organization hierarchy |
| `statuses` | File status tracking (Draft, Active, etc.) |
| `templates` | Folder structure templates (stores subfolder paths) |
| `client` | Client information |
| `batch_list` | Project batch grouping |
| `teams` | User/team member management |
| `wallet_pockets` / `wallet_cards` | Financial accounts |
| `wallet_transactions` | Transaction records |
| `microstock_platforms` | Microstock platform settings |
| `file_microstock_status` | File upload status per platform |

Run migrations are in `database/migrations/` and apply automatically on startup.

## Development 🧑‍💻

```
├── main.py               # Application entry point
├── gui/                  # PySide6 UI components
│   ├── windows/         # Main window and dialogs
│   └── widgets/         # Reusable UI widgets
├── database/            # Database layer
│   ├── migrations/      # SQL migration files
│   └── db_helper/       # Database helper classes
└── configs/             # Configuration files
```

## License 📄

MIT License - see [LICENSE](LICENSE) file for details.