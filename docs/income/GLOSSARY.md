# Onto Glossary

## Status
- State: draft canonical glossary
- Source: user-provided glossary seed, normalized on `2026-04-16`
- Language: Russian

## Usage Rules
- Use these definitions as the current normalized vocabulary for Onto domain documentation and MCP semantics.
- If another repository uses a different term or meaning, preserve that difference explicitly instead of overwriting this glossary.
- Mark synonyms and references with `Alias of` notes.

## Terms

### База знаний Онто
- Definition: База знаний, включающая в себя все объекты и связи одного пространства Онто.
- Notes: Scope is limited to a single Onto space.

### Пространство
- Definition: Отдельная рабочая область, элементы которой изолированы от других пространств.

### Контекст
- Definition: Логический контейнер внутри пространства, в котором размещаются связанные сущности: объекты, связи и диаграммы. Он определяет рамки для построения смысловой модели.
- Notes: This is not the same as UI context unless a source states otherwise.

### Диаграмма
- Definition: Онлайн-доска, на которой пользователи пространства могут работать с элементами этого пространства.

### Визуальный контекст
- Definition: См. `Диаграмма`.
- Alias of: `Диаграмма`

### Объект базы знаний
- Definition: Отдельная запись в базе знаний Онто. Представляет собой декларативное описание сущностей материального и нематериального мира, обладающих набором характеристик и связей с другими объектами.

### Объект-шаблон
- Definition: Объект, созданный на платформе, который одновременно играет роль шаблона и может использоваться на диаграмме.
- Notes: Derived from both `Объект базы знаний` and `Шаблон`.
- Current product rule: In the current Onto model, users create `Объекты-шаблоны`, not standalone `Шаблоны`.
- Example: Объект-шаблон `Кот` может использоваться на диаграмме `Виды животных`.

### Шаблон
- Definition: Набор предустановленных свойств, применяемых к объекту для стандартизации и упрощения управления.
- Notes: In current product behavior this concept is realized through `Объект-шаблон`, not as a separately created runtime entity.

### Поля шаблона
- Definition: Свойства, описанные в шаблоне, которые могут иметь объекты этого шаблона.

### Шаблонные поля
- Definition: Свойства объекта, полученные на основе шаблона, примененного к объекту.

### Поля объекта
- Definition: Список свойств конкретного объекта, которые пользователь может добавить дополнительно к шаблонным полям.

### Связь
- Definition: Отношение между двумя элементами базы знаний.

### Шаблон связи
- Definition: Описание возможного типа связи между двумя шаблонами. Определяет правила и характеристики экземпляров связей.

### Шаблонная связь
- Definition: Конкретная связь между двумя объектами, созданная на основе ранее определенного шаблона связи.

### Представление объекта на диаграмме
- Definition: Визуальное отображение на диаграмме знания из базы Онто, имеющего шаблон.

### Представление связи на диаграмме
- Definition: Визуальное отображение на диаграмме знания из базы Онто о связи между двумя объектами.

### Представление шаблона на диаграмме
- Definition: Визуальное отображение на диаграмме знания из базы Онто о части метамодели.

## Open Questions
- Does every object shown on a diagram require a template, or only the object representation term does?
- Should `Контекст` and `Диаграмма` remain distinct entities in the metamodel, or is one a view of the other?
