# DESTRO_CRM

CRM operacional em `Python + Streamlit` para montagem de tabloides, geração de artes e PDFs comerciais, com base em planilha Excel e banco de imagens local.

## Visão executiva

O projeto está consolidado com foco em uso real:

- Fluxos críticos funcionais validados (montagem, filtros, geração de PDF/tabloide/artes)
- Estabilidade e mensagens claras para falhas de planilha/imagem
- Performance otimizada com cache e redução de reruns desnecessários
- UX/UI modernizada com hierarquia visual por etapas
- Robustez de dados/imagens com módulos dedicados e metadados
- Suíte mínima de testes automatizados com `pytest` (14 testes)

## Arquitetura atual

### Módulos principais

- `app.py`
  - ponto de entrada Streamlit
  - orquestra interface, estado de sessão e chamadas de geração
- `data_loader.py`
  - carga e validação robusta da planilha
  - warnings e códigos de erro para estrutura inválida/corrompida
- `image_manager.py`
  - indexação de imagens
  - upload/substituição segura com backup e metadados
- `core_utils.py`
  - funções puras reutilizáveis/testáveis (validação upload, normalização numérica, preparo de dataframe)
- `tests/`
  - suíte de testes automatizados (`pytest`)

### Fluxo de dependências

`app.py -> data_loader.py`

`app.py -> image_manager.py`

`app.py -> core_utils.py`

### Ponto de entrada

```bash
streamlit run app.py
```

## Dependências externas

- Planilha principal: `Programa_Destro-04-03.xlsx`
- Banco de imagens: pasta `Base de Imagens/`
- Fontes tipográficas: pasta `Fontes/`
- Metadados de imagem: `Base de Imagens/image_metadata.json`
- Backups automáticos de imagens: `Base de Imagens/_backup/`

## Estrutura de pastas atual (consolidada)

```text
DESTRO_CRM/
  app.py
  data_loader.py
  image_manager.py
  core_utils.py
  requirements.txt
  requirements-dev.txt
  tests/
    test_core_utils.py
    test_data_loader.py
    test_image_manager.py
  Base de Imagens/
    image_metadata.json
    _backup/
  Fontes/
  Programa_Destro-04-03.xlsx
```

## Estrutura de pastas sugerida (evolução controlada)

```text
DESTRO_CRM/
  app/
    app.py
    data_loader.py
    image_manager.py
    core_utils.py
  tests/
  data/
    Programa_Destro-04-03.xlsx
  images/
    Base de Imagens/
    image_metadata.json
    _backup/
  docs/
    README.md
    architecture.md
  requirements.txt
  requirements-dev.txt
```

> Observação: a sugestão acima é organizacional para próxima etapa. O estado atual já está funcional e validado.

## Instalação e execução

### 1) Clonar repositório

```bash
git clone https://github.com/sgcarloseduardo-maker/DESTRO_CRM
cd DESTRO_CRM
```

### 2) Criar ambiente virtual (recomendado)

Windows (PowerShell):

```bash
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Instalar dependências de app

```bash
pip install -r requirements.txt
```

### 4) Rodar o app

```bash
streamlit run app.py
```

## Testes automatizados

### Instalar dependências de teste

```bash
pip install -r requirements-dev.txt
```

### Executar suíte

```bash
pytest tests/ -v
```

Resultado esperado atual: `14 passed`.

## Checklist de regressão funcional (manual)

1. Abrir o app e navegar entre abas.
2. Aplicar filtros (ABC, campanhas, cascata de indústria/marca/categoria).
3. Adicionar/remover/reordenar itens no painel.
4. Gerar:
   - `GERAR TABLOIDE (GRADE)`
   - `GERAR ARTES INDIVIDUAIS`
   - `GERAR PDF PLANILHA`
5. Confirmar download dos arquivos gerados.
6. Subir/trocar imagem de produto e validar:
   - atualização visual
   - backup em `_backup`
   - atualização no `image_metadata.json`
7. Simular planilha ausente/corrompida/estrutura inválida e validar mensagens + logs.

## Operação de planilhas e imagens

### Atualizar planilha

1. Substituir `Programa_Destro-04-03.xlsx` mantendo o nome.
2. Reiniciar app ou usar "Forçar atualização completa".
3. Verificar expander de avisos da base no sidebar.

### Adicionar/substituir imagem

1. Localizar produto na montagem.
2. Usar `Subir`/`Trocar`.
3. Confirmar sucesso e geração com nova imagem.
4. Conferir metadados em `Base de Imagens/image_metadata.json`.

## Troubleshooting

### "Planilha não encontrada"

- Verifique se `Programa_Destro-04-03.xlsx` está no diretório raiz do projeto.

### "Planilha inválida/corrompida"

- Abra o arquivo no Excel e valide integridade.
- Reexporte/copie uma versão íntegra.

### Upload de imagem falha

- Verifique formato permitido (`.jpg`, `.jpeg`, `.png`, `.webp`)
- Verifique tamanho máximo configurado
- Verifique permissões de escrita na pasta `Base de Imagens`

### App lento em geração

- Em lotes grandes, geração de arte/PDF pode levar alguns segundos.
- Use os spinners e aguarde finalização do processamento.

## Critérios finais de aceite (produção)

- Funcionalidade: fluxos críticos operam de ponta a ponta sem erro bloqueante.
- Performance: sem regressão relevante frente baseline da Fase 3.
- UX/UI: navegação clara por etapas e feedbacks consistentes.
- Dados/Imagens: tratamento robusto de erro, warnings úteis, metadados e backup.
- Testes: suíte automatizada passando 100%.
- Segurança básica: sem exposição acidental de caminhos sensíveis na UI.
- Deploy: ambiente reproduzível via `requirements.txt` e `requirements-dev.txt`.

## Próximos passos (opcional)

- Autenticação/autorização completa por perfil.
- Banco de dados externo para dados transacionais.
- Storage de imagens em nuvem (S3/Blob) com versionamento.
- CI/CD para rodar testes automáticos a cada push/PR.

