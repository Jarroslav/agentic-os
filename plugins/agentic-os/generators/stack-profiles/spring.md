# Stack profile: spring

Java/Kotlin service on Spring Boot with Maven or Gradle.

## Detection markers

- `pom.xml` with `spring-boot-starter-*` dependencies, or
- `build.gradle` / `build.gradle.kts` with the Spring Boot plugin
- `src/main/java/` or `src/main/kotlin/`

## Variable defaults

| Variable | Default |
|---|---|
| `{{MIGRATIONS_DIR}}` | `src/main/resources/db/migration/` (Flyway) or `src/main/resources/db/changelog/` (Liquibase); empty if neither exists ⇒ migration hooks skipped |
| `{{GATE_COMMANDS}}` | Maven: `./mvnw -q verify` · Gradle: `./gradlew check` (includes compile + unit tests; add the configured linter, e.g. `spotlessCheck`/`checkstyle`, when present) |
| `{{MIGRATION_DIFF_COMMAND}}` | Flyway: `./mvnw flyway:validate` (or Gradle `flywayValidate`) · Liquibase: `liquibase validate` — pick per detected tool |
| `{{ENV_CHECK_COMMANDS}}` | `java -version` · `./mvnw -v` or `./gradlew -v` |
| `{{APP_START_COMMAND}}` | `./mvnw spring-boot:run` or `./gradlew bootRun` |
| `{{BASE_URL}}` | `http://localhost:8080` |

## Generated-agent slots that apply

`gen/schema-architect` (Flyway/Liquibase migration files — versioned,
append-only), `gen/api-author`, `gen/migration-validator`,
`gen/stack-guides`. `gen/component-generator` and `gen/i18n-agent` only when
a frontend module / `messages*.properties` bundles are detected.

## Capability map

Structured counterpart to "Generated-agent slots that apply" above, in the
exact field names `generators/stack-discovery.md`'s confirm-only mode emits
— read this table directly instead of re-deriving it from prose.

| Capability | `applies` | paradigm / style | `write_scope` |
|---|---|---|---|
| `persistence` | `true` | `migration-managed`; `access_control_style: "Spring Security method security (@PreAuthorize)"` | `{{MIGRATIONS_DIR}}**` |
| `server_writes` | `true` | `api_style: "REST (@RestController + DTOs)"` | `src/main/{java,kotlin}/**` |
| `ui` | conditional — `true` only when a frontend module is detected, else `false` | `component-framework` (when present) | the frontend module's own component directory |
| `i18n` | conditional — `true` only when `messages*.properties` bundles are detected, else `false` | `catalog_format: "Java ResourceBundle .properties"` | `src/main/resources/messages*.properties` |

## Stack facts for the generators

- **ORM**: JPA/Hibernate entities; schema truth lives in the migration files,
  not `ddl-auto` (flag `ddl-auto: update` in a non-dev profile under
  `## Blocking` in generated gate agents). Flyway naming:
  `V<version>__<description>.sql`; existing versioned migrations are
  immutable — never edit an applied one.
- **API idiom**: `@RestController` + DTOs with Bean Validation
  (`@Valid`, `jakarta.validation` annotations); mapping via the repo's
  chosen mapper (MapStruct etc.). Exceptions via `@ControllerAdvice`.
- **Auth/access**: Spring Security filter chain / method security
  (`@PreAuthorize`) — reuse the existing configuration's idiom.
- **Test runner**: JUnit 5 (+ Testcontainers when present for DB tests);
  `@SpringBootTest` sparingly, slice tests preferred.
- **Build discipline**: the wrapper (`mvnw`/`gradlew`) is the only build
  entry point agents use — never a globally installed mvn/gradle.
