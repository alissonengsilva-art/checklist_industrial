CREATE TABLE checklist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tecnico VARCHAR(80),
    tipo_sistema VARCHAR(80),
    dados_json TEXT,
    comentarios TEXT,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
);
