# Setup Instructions for Windows Users

## Prerequisites
1. **Git**: Install Git from [git-scm.com](https://git-scm.com/download/win).
2. **Node.js**: Download and install Node.js from [nodejs.org](https://nodejs.org/).
3. **Database**: Set up a database (e.g., MySQL or PostgreSQL) on your machine.

## Database Configuration
1. Create a new database for the application.
2. Update the `database/config.json` file with the following information:
   - **host**: `localhost`
   - **user**: `your_db_user`
   - **password**: `your_db_password`
   - **database**: `your_db_name`

## Environment Variables
Create a `.env` file in the root of the project and add the following settings:
```
DB_HOST=localhost
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name
PORT=3000
```
Make sure to replace `your_db_user`, `your_db_password`, and `your_db_name` with your actual database credentials.

## Running the Application
1. Open a terminal and navigate to the project directory.
2. Install the dependencies by running:
   ```bash
   npm install
   ```
3. Start the application with:
   ```bash
   npm start
   ```
4. You should now be able to access the application at `http://localhost:3000`.

## Troubleshooting
- If you encounter issues connecting to the database, double-check your credentials and ensure the database server is running.
- Check the application logs for any errors that may indicate configuration issues.