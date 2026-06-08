from flask import Flask, jsonify, request, send_file
from neo4j import GraphDatabase
import os

app = Flask(__name__)

URI = "neo4j+s://1b8257fc.databases.neo4j.io"
USER = "1b8257fc"
PASSWORD = os.environ.get("NEO4J_PASSWORD", "zZsf__hCU6K57kozZhVRnOVy2KhRf-GcIWlflZbDlvo")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

@app.route("/")
def index():
    return send_file("index.html")

@app.route("/api/search")
def search():
    keyword = request.args.get("q", "")
    limit = int(request.args.get("limit", 20))
    with driver.session() as session:
        result = session.run("""
            MATCH (q:Question)
            WHERE q.text CONTAINS $keyword
            RETURN q.id AS id, q.text AS question, q.answer AS answer,
                   q.type AS type, q.level AS level
            LIMIT $limit
        """, keyword=keyword, limit=limit)
        return jsonify([r.data() for r in result])

@app.route("/api/multihop/<qid>")
def multihop(qid):
    with driver.session() as session:
        result = session.run("""
            MATCH (q:Question {id: $id})
            OPTIONAL MATCH (q)-[:SUPPORTED_BY]->(s:Sentence)<-[:CONTAINS]-(c:Context)
            RETURN q.text AS question, q.answer AS answer, q.type AS type,
                   collect(DISTINCT {sentence: s.text, article: c.title}) AS paths
        """, id=qid)
        record = result.single()
        return jsonify(record.data()) if record else (jsonify({"error": "Not found"}), 404)

@app.route("/api/stats")
def stats():
    with driver.session() as session:
        result = session.run("MATCH (q:Question) RETURN q.type AS type, count(q) AS count ORDER BY count DESC")
        return jsonify([r.data() for r in result])

@app.route("/api/cluster")
def cluster():
    with driver.session() as session:
        result = session.run("""
            MATCH (q:Question)
            RETURN q.type AS type, q.level AS level, count(q) AS count
            ORDER BY type, level
        """)
        data = {}
        for r in result:
            t = r["type"]
            if t not in data:
                data[t] = []
            data[t].append({"level": r["level"], "count": r["count"]})
        return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
