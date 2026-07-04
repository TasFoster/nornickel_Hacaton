# Запуск локального портативного Neo4j (тестирование без Aura).
# Портативная установка (JRE + Neo4j Community 5.26) создана в C:\Users\farcr\nornicel-neo4j.
# Оставьте это окно открытым — сервер работает, пока оно живо.
# Neo4j Browser: http://localhost:7474  (логин neo4j / пароль из .env)
$base = "C:\Users\farcr\nornicel-neo4j"
$env:JAVA_HOME = "$base\jre\jdk-21.0.11+10-jre"
Write-Host "JAVA_HOME = $env:JAVA_HOME"
Write-Host "Запуск Neo4j (bolt://localhost:7687)..."
& "$base\neo4j-community-5.26.0\bin\neo4j.bat" console
