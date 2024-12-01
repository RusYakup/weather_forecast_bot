from postgres.sqlfactory import SQLQueryBuilder


def test_select():
    fields = ["chat_id", "city", "last_name"]
    builder = SQLQueryBuilder("users")
    builder.select(fields)
    assert builder.sql == "SELECT chat_id, city, last_name FROM users"
    assert builder.args == []


def test_delete():
    builder = SQLQueryBuilder("users_table")
    builder.delete()
    assert builder.sql == "DELETE FROM users_table"
    assert builder.args == []


def test_where():
    builder = SQLQueryBuilder("users")
    builder.select(["chat_id", "city"])
    fields = {
        "chat_id": ("=", "1809"),
        "city": ("=", "Kazan"),
    }
    builder.where(fields)
    assert builder.sql == "SELECT chat_id, city FROM users WHERE chat_id = $1 AND city = $2"
    assert builder.args == ["1809", "Kazan"]


def test_limit():
    builder = SQLQueryBuilder("users")
    builder.select(["chat_id", "city"])
    builder.limit(10)
    assert builder.sql == "SELECT chat_id, city FROM users LIMIT $1"
    assert builder.args == [10]


def test_order_by():
    builder = SQLQueryBuilder("users")
    builder.select(["chat_id", "city"])
    builder.order_by("chat_id", "DESC")
    assert builder.sql == "SELECT chat_id, city FROM users ORDER BY chat_id DESC"
    assert builder.args == []


def test_group_by():
    builder = SQLQueryBuilder("users")
    builder.select(["chat_id", "city"])
    builder.group_by(["chat_id", "city"])
    assert builder.sql == "SELECT chat_id, city FROM users GROUP BY chat_id, city"
    assert builder.args == []


def test_update():
    builder = SQLQueryBuilder("users")
    fields = {
        "city": "Moskva",
        "date_difference": "waiting_value",
    }
    builder.update(fields)
    assert builder.sql == "UPDATE users SET city = $1, date_difference = $2"
    assert builder.args == ["Moskva", "waiting_value"]


def test_insert():
    """
    Tests the insert function in the sqlfactory module.
    The following tests are performed:
    1. A basic insert statement with three fields.
    2. An insert statement with an on conflict clause.
    3. An insert statement with an on conflict clause and do update clause with a single field.
    """
    table = "users"
    fields = {
        "chat_id": "1809",
        "city": "Kazan",
        "last_name": "Yakupov",
    }
    builder = SQLQueryBuilder(table)
    builder.insert(fields)
    assert builder.sql == 'INSERT INTO users (chat_id, city, last_name) VALUES ($1, $2, $3)'
    assert builder.args == ['1809', 'Kazan', 'Yakupov']

    builder = SQLQueryBuilder(table)
    builder.insert(fields, on_conflict="chat_id")
    assert builder.sql == 'INSERT INTO users (chat_id, city, last_name) VALUES ($1, $2, $3) ON CONFLICT (chat_id) DO NOTHING'
    assert builder.args == ['1809', 'Kazan', 'Yakupov']

    builder = SQLQueryBuilder(table)
    builder.insert(fields, on_conflict="chat_id", update_fields=["city"])
    assert builder.sql == 'INSERT INTO users (chat_id, city, last_name) VALUES ($1, $2, $3) ON CONFLICT (chat_id) DO UPDATE SET city = EXCLUDED.city'
    assert builder.args == ['1809', 'Kazan', 'Yakupov']
