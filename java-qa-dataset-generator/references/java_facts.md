# Java Facts Reference

Verified facts that language models often get wrong. When an answer mentions any of these, use the values here.
If a fact you need is not listed and you are not certain, describe the behaviour without stating a specific number, version or name.

## Java releases
- LTS releases: **8, 11, 17, 21, 25** (25 released September 2025). New feature releases every 6 months (March and September).
- **Dataset baseline: Java 21.** Code must compile on 21 unless the topic is a newer feature.

## When features became final (standard)

| Feature | Final in |
|---|---|
| Lambdas, streams, `Optional`, `java.time`, default methods | 8 |
| Modules (JPMS), `jshell`, `List.of`/`Set.of`/`Map.of`, private interface methods, try-with-resources on effectively final vars, diamond with anonymous classes | 9 |
| `var` for local variables | 10 |
| `HttpClient` (`java.net.http`), `var` in lambda parameters, `String.isBlank/strip/lines/repeat`, `Files.readString/writeString`, single-file source launch (`java Main.java`) | 11 |
| Switch expressions (`->`, `yield`) | 14 |
| Helpful NullPointerException messages (on by default from 15) | 14 |
| Text blocks; Nashorn removed; ZGC and Shenandoah production-ready | 15 |
| Records; pattern matching for `instanceof`; `Stream.toList()` | 16 |
| Sealed classes/interfaces; strong encapsulation of JDK internals (`--illegal-access` removed) | 17 |
| UTF-8 as default charset (JEP 400); simple web server `jwebserver` | 18 |
| Virtual threads; pattern matching for `switch`; record patterns; sequenced collections; generational ZGC (opt-in via `-XX:+ZGenerational`) | 21 |
| Unnamed variables and patterns (`_`); Foreign Function & Memory API; launching multi-file source programs | 22 |
| Generational mode becomes the ZGC default | 23 |
| Stream Gatherers (`Stream.gather`); Class-File API; virtual threads no longer pinned by `synchronized` (JEP 491); non-generational ZGC removed; Security Manager permanently disabled (JEP 486) | 24 |
| Scoped values; module import declarations; compact source files and instance `main` methods; flexible constructor bodies | 25 |

**Still preview (do not call them final):** structured concurrency (`StructuredTaskScope`, still preview in 25); primitive types in patterns. **Incubator:** Vector API.
**Withdrawn:** string templates (previewed in 21 and 22, removed in 23). Never show `STR."..."` as usable.
**Deprecated or removed:** Security Manager (deprecated for removal in 17, disabled in 24); finalization (deprecated for removal in 18); `Thread.stop()` throws `UnsupportedOperationException` (since 20); applets removed; `javax.*` Java EE packages are `jakarta.*` from Jakarta EE 9 on.

## Language and core library facts
- `Integer.valueOf` / autoboxing caches **-128 to 127**. The upper bound can be raised with `-XX:AutoBoxCacheMax`. `Byte`, `Short`, `Long` and `Character` (0–127) also cache; `Float` and `Double` do not.
- Java is **always pass-by-value**; object references are copied by value.
- `char` is a UTF-16 code unit; characters outside the BMP (such as emoji) take two `char`s. Use `codePoints()`.
- Integer overflow wraps silently. Use `Math.addExact`/`multiplyExact` to get an `ArithmeticException` instead. Integer division by zero throws `ArithmeticException`; floating-point division by zero gives `Infinity` or `NaN`.
- `String.hashCode` is cached; compact strings (Latin-1 storage) since 9; switch on `String` uses `hashCode` plus `equals`.
- `var`: local variables with an initializer only; not for fields, method parameters or return types; `var x = null;` is illegal.
- Records: implicitly `final`; components are `private final`; they cannot extend a class (they implicitly extend `java.lang.Record`) but can implement interfaces; no instance fields besides the components; static fields and methods are allowed; there is a compact canonical constructor.
- Sealed: permitted subclasses must be `final`, `sealed` or `non-sealed`, and must be in the same module (or the same package when unnamed).
- Pattern `switch`: must be exhaustive; `case null` is allowed (otherwise a null selector throws NPE); a guarded `case X x when cond` must come before an unguarded `case X x`, or the compiler reports a dominance error.
- Interfaces: fields are implicitly `public static final`; methods are `public abstract` unless `default`, `static` or `private`.

## Collections
- `ArrayList`: default capacity 10 (allocated lazily on the first add); grows by about 1.5×; `get` O(1); insert or remove in the middle O(n).
- `HashMap`: default capacity 16, load factor 0.75, resizes by doubling; a bucket turns into a red-black tree when it holds ≥ 8 entries **and** the table capacity is ≥ 64 (otherwise the table is resized); it turns back into a list at ≤ 6. One `null` key is allowed. Iteration order is not guaranteed.
- `ConcurrentHashMap`, `Hashtable`: **no** null keys or values.
- `TreeMap`/`TreeSet`: O(log n); natural ordering rejects a `null` key (NPE).
- `List.of`, `Set.of`, `Map.of`: unmodifiable, **reject nulls**; `Set.of`/`Map.of` reject duplicates; `Map.of` takes up to 10 key-value pairs (use `Map.ofEntries` for more); iteration order of `Set.of`/`Map.of` is unspecified.
- `Arrays.asList`: fixed size (`add`/`remove` throw `UnsupportedOperationException`; `set` works); backed by the array.
- `Collections.unmodifiableList` returns a **view**: changes to the original show through. `List.copyOf` makes an independent copy.
- `Collectors.toList()` makes no guarantee about mutability (in practice an `ArrayList`). `Stream.toList()` (16) returns an unmodifiable list that **allows nulls**.
- Fail-fast iterators throw `ConcurrentModificationException` on a best-effort basis; concurrent collections have weakly consistent iterators.
- Sequenced collections (21): `getFirst()`, `getLast()`, `reversed()`, `addFirst()`, `addLast()` on `List`, `Deque`, `LinkedHashSet`, `LinkedHashMap` (`firstEntry`, `pollFirstEntry`, …), `SortedSet`/`SortedMap`.

## Streams and functional programming
- Streams are lazy; nothing runs until a terminal operation; a stream can be consumed only once (`IllegalStateException` on reuse).
- Parallel streams use the common `ForkJoinPool` (size ≈ available processors − 1).
- `Optional`: not `Serializable`; don't use it for fields or parameters; `orElse` always evaluates its argument, `orElseGet` evaluates lazily; `Optional.get()` throws `NoSuchElementException` when empty (prefer `orElseThrow()`, available since 10).
- `Collectors.toMap` throws `IllegalStateException` on duplicate keys unless you pass a merge function; it also throws NPE on null values.

## Concurrency
- `volatile` gives visibility and ordering, **not atomicity** for compound actions (`count++`).
- Happens-before edges: unlocking a monitor → later locking of the same monitor; a volatile write → a later volatile read of the same variable; `Thread.start()`; `Thread.join()`; actions in an `ExecutorService` task → `Future.get()`.
- `LongAdder`: `sum()` is not an atomic snapshot; there is no `incrementAndGet`.
- Virtual threads (21): cheap, managed by the JVM, mounted on carrier threads (a `ForkJoinPool`). **Don't pool them**; use `Executors.newVirtualThreadPerTaskExecutor()`. Blocking inside `synchronized` pinned the carrier in 21–23 (fixed in 24, JEP 491). Native/JNI frames still pin.
- `ExecutorService` implements `AutoCloseable` since 19 (`close()` waits for submitted tasks to finish).
- `CompletableFuture` async methods without an executor use `ForkJoinPool.commonPool()`. `join()` throws an unchecked `CompletionException`; `get()` throws the checked `ExecutionException`.
- `wait`/`notify` must be called while holding the object's monitor, otherwise `IllegalMonitorStateException`. Always call `wait` in a loop (spurious wakeups).
- `SimpleDateFormat` and `HashMap` are not thread-safe; `DateTimeFormatter` is immutable and thread-safe.

## JVM and GC
- Default GC: **G1** since 9 (Serial is chosen automatically on small machines: < 2 CPUs or < 1792 MB of memory).
- Metaspace replaced PermGen in **8**.
- Default maximum heap: ¼ of physical memory (or of the container limit); in containers use `-XX:MaxRAMPercentage`. Container awareness is on by default (since 10 / 8u191).
- GC logging since 9: `-Xlog:gc*` (old `-XX:+PrintGCDetails` is deprecated).
- G1 humongous object: ≥ 50% of a region.
- Tiered compilation: interpreter → C1 → C2 (on by default since 8).
- Class loaders (9+): bootstrap → platform → application (system). Parent-first delegation.

## Ecosystem
- **Spring Boot 3.x** needs Java 17+, uses `jakarta.*` and Spring Framework 6. `RestClient` from Spring Framework 6.1 / Boot 3.2. Virtual threads: `spring.threads.virtual.enabled=true` (Boot 3.2+).
- **Spring Security 6:** `WebSecurityConfigurerAdapter` is **removed**; define a `SecurityFilterChain` `@Bean`. `authorizeHttpRequests` with `requestMatchers` (`antMatchers` was removed). CSRF protection is enabled by default.
- `@Transactional` on a method called from the **same class** (self-invocation) is not applied (proxy-based). By default it rolls back only on unchecked exceptions and `Error`.
- Constructor injection is recommended over field injection.
- **JUnit 5:** `org.junit.jupiter.api.Test`, `Assertions.assertThrows`, `@BeforeEach`/`@AfterEach`/`@BeforeAll`/`@AfterAll`, `@ParameterizedTest` (in the `junit-jupiter-params` artifact; included in the `junit-jupiter` aggregate). There is no `@Test(expected=…)` (that was JUnit 4).
- **Mockito 5:** the inline mock maker is the default, so `mockStatic` and final classes work without extra configuration. `mockStatic` returns a `MockedStatic` that must be closed (use try-with-resources).
- **Hibernate 6 / JPA 3:** `jakarta.persistence.*`. Default fetch: `@ManyToOne` and `@OneToOne` are EAGER; `@OneToMany` and `@ManyToMany` are LAZY.
- Maven: lifecycle `validate → compile → test → package → verify → install → deploy`; scopes `compile` (default), `provided`, `runtime`, `test`, `system`, `import` (BOMs only).
- Gradle: `compile` and `testCompile` were removed in Gradle 7; use `implementation`, `api` (needs the `java-library` plugin), `compileOnly`, `runtimeOnly`, `testImplementation`.

## Security reference
- **OWASP Top 10 (2021):** A01 Broken Access Control, A02 Cryptographic Failures, A03 Injection (includes XSS), A04 Insecure Design, A05 Security Misconfiguration (includes XXE), A06 Vulnerable and Outdated Components, A07 Identification and Authentication Failures, A08 Software and Data Integrity Failures (includes insecure deserialization), A09 Security Logging and Monitoring Failures, A10 Server-Side Request Forgery.
- **OWASP API Security Top 10 (2023):** API1 Broken Object Level Authorization, API2 Broken Authentication, API3 Broken Object Property Level Authorization, API4 Unrestricted Resource Consumption, API5 Broken Function Level Authorization, API6 Unrestricted Access to Sensitive Business Flows, API7 Server Side Request Forgery, API8 Security Misconfiguration, API9 Improper Inventory Management, API10 Unsafe Consumption of APIs.
- **CWE IDs:** CWE-20 improper input validation, CWE-22 path traversal, CWE-78 OS command injection, CWE-79 XSS, CWE-89 SQL injection, CWE-90 LDAP injection, CWE-117 log injection, CWE-190 integer overflow, CWE-200 information exposure, CWE-209 error message info leak, CWE-250 unnecessary privileges, CWE-269 improper privilege management, CWE-284 improper access control, CWE-285 improper authorization, CWE-287 improper authentication, CWE-295 improper certificate validation, CWE-306 missing authentication for critical function, CWE-311 missing encryption, CWE-327 broken crypto algorithm, CWE-330 insufficient randomness, CWE-352 CSRF, CWE-362 race condition, CWE-367 TOCTOU, CWE-384 session fixation, CWE-400 uncontrolled resource consumption, CWE-434 unrestricted file upload, CWE-502 deserialization of untrusted data, CWE-601 open redirect, CWE-611 XXE, CWE-639 authorization bypass via user-controlled key (IDOR), CWE-770 allocation without limits, CWE-798 hard-coded credentials, CWE-862 missing authorization, CWE-863 incorrect authorization, CWE-915 mass assignment, CWE-917 expression language injection, CWE-918 SSRF, CWE-1333 ReDoS.
- **Log4Shell:** CVE-2021-44228, Log4j 2.0-beta9 through 2.14.1, JNDI lookup in logged strings. Follow-up CVEs: CVE-2021-45046 (2.15.0 incomplete fix), CVE-2021-45105 (DoS, fixed in 2.17.0), CVE-2021-44832 (fixed in 2.17.1). Recommend **2.17.1+** (Java 8), 2.12.4+ (Java 7), 2.3.2+ (Java 6).
- **Crypto in Java:**
  - `Cipher.getInstance("AES/GCM/NoPadding")` with a 12-byte random IV, `GCMParameterSpec(128, iv)`, and **never reuse an IV with the same key**.
  - `"AES"` alone defaults to ECB mode, which is insecure. RSA: `"RSA/ECB/OAEPWithSHA-256AndMGF1Padding"`.
  - `SecureRandom` for tokens and keys, never `Random` or `Math.random()`. Compare MACs and tokens with `MessageDigest.isEqual`.
- **Password hashing (OWASP):** Argon2id (minimum m=19 MiB, t=2, p=1), scrypt, bcrypt (cost ≥ 10; inputs over 72 bytes are truncated), PBKDF2-HMAC-SHA256 with ≥ 600,000 iterations. Never use plain SHA-256 or MD5.
- **NIST SP 800-63B passwords:** minimum 8 characters (15 when it is the only factor, per revision 4); allow at least 64; no forced periodic rotation; no composition rules; check against breached-password lists.
- **JWT:** reject `alg: none`; pin the expected algorithm; validate `exp`, `nbf`, `iss` and `aud`; never put secrets in the payload (it is only Base64url-encoded).
- **XXE fix:** `factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)`.
- **Deserialization:** `ObjectInputFilter` (JEP 290, Java 9, backported to 8u121); `jdk.serialFilter` system property; context-specific filter factories (JEP 415, Java 17).
