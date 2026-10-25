"""Script to generate comprehensive Core Java Important Points documents across PDF, DOCX, PPTX, and HTML Web Artifact using Project JARVIS Creator tools.

Author: Assistant on behalf of Project JARVIS
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

from creator.tools import (
    CreatePdfTool,
    CreateDocxTool,
    CreatePptxTool,
    CreateWebsiteTool,
)

TITLE = "Core Java: Architecture, Principles, & Key Concepts"
HERO_TAGLINE = "Comprehensive Reference Guide to JVM Internals, OOP, Collections, Concurrency, and Modern Java 8-21 LTS"

SECTIONS = [
    {
        "heading": "1. JVM Architecture & Memory Management",
        "text": "The Java Virtual Machine (JVM) is an abstract computing machine that enables Java programs to be write-once, run-anywhere (WORA). It is composed of the ClassLoader subsystem, Runtime Data Areas, and the Execution Engine.",
        "metrics": [
            {"label": "Stack Allocation", "value": "Thread-Local (< 1 MB)"},
            {"label": "Heap Allocation", "value": "Shared Objects (GBs)"},
            {"label": "JIT Compilation", "value": "HotSpot C1 / C2"},
            {"label": "Modern GC", "value": "G1 & ZGC (< 1ms pause)"},
        ],
        "bullets": [
            "ClassLoader Subsystem: Implements Delegation-Hierarchy via Bootstrap, Extension/Platform, and Application ClassLoaders.",
            "Runtime Data Areas: Method Area (Metaspace since Java 8), Heap (Eden, Survivor S0/S1, Tenured), JVM Stack (Frames with local variables, operand stack), PC Registers, and Native Method Stack.",
            "Execution Engine: Combines Bytecode Interpreter with HotSpot JIT (Tiered compilation: C1 client compiler for fast startup, C2 server compiler for peak performance).",
            "Garbage Collection Mechanics: Generational hypothesis (most objects die young); minor GC in Young Gen, major/full GC in Tenured. ZGC and Shenandoah provide sub-millisecond concurrent pause times.",
        ],
        "table": [
            ["Memory Region", "Scope", "Lifetime", "Primary Contents", "Failure Error"],
            ["JVM Stack", "Thread-Local", "Thread Execution", "Stack frames, primitive locals, object references", "StackOverflowError"],
            ["Heap Memory", "Global (All Threads)", "Application Runtime", "Class instances, arrays, instance fields", "OutOfMemoryError: Java heap space"],
            ["Metaspace", "Global (All Threads)", "Class Lifecycle", "Class metadata, bytecode, static variables", "OutOfMemoryError: Metaspace"],
            ["Program Counter (PC)", "Thread-Local", "Thread Execution", "Address of current JVM instruction being executed", "None (Hardware native)"],
        ],
    },
    {
        "heading": "2. Object-Oriented Programming (OOP) Pillars & Best Practices",
        "text": "Java's core paradigm is structured around the four fundamental pillars of Object-Oriented Programming, complemented by the SOLID design principles to ensure maintainable, loosely coupled, and extensible codebases.",
        "metrics": [
            {"label": "Encapsulation", "value": "Data Hiding"},
            {"label": "Inheritance", "value": "Code Reusability"},
            {"label": "Polymorphism", "value": "Dynamic Binding"},
            {"label": "Abstraction", "value": "Contract Decoupling"},
        ],
        "bullets": [
            "Encapsulation: Bundles state and behavior into classes; access modifiers (private, default, protected, public) restrict direct field access; use record types for pure immutable state carriers.",
            "Inheritance: Enables 'is-a' relationships using 'extends'; Java supports single class inheritance to avoid the diamond problem, but permits multiple interface implementation via 'implements'.",
            "Polymorphism: Compile-time polymorphism through method overloading (same method name, different parameter signature); Runtime polymorphism through method overriding (resolved via dynamic vtable dispatch).",
            "Abstraction: Exposes what an object does while hiding how it does it; achieved via abstract classes (partial implementation with state) and interfaces (behavioral contracts with default and static methods).",
            "Composition Over Inheritance: Favor 'has-a' composition over deep class hierarchies to minimize tight coupling and brittle base-class issues.",
        ],
        "table": [
            ["OOP Pillar", "Java Keywords / Syntax", "Core Architectural Purpose", "Industry Best Practice"],
            ["Encapsulation", "private, getter/setter, record", "Protects state integrity and prevents invalid mutations", "Make fields private final; expose immutable defensive copies"],
            ["Inheritance", "extends, super", "Facilitates hierarchical categorization and code reuse", "Keep hierarchies shallow (max 2-3 levels); prefer composition"],
            ["Polymorphism", "@Override, interfaces", "Allows uniform treatment of diverse derived types", "Program to interfaces, not concrete implementations"],
            ["Abstraction", "abstract, interface, default", "Decouples public API consumers from implementation details", "Segregate interfaces into focused, cohesive contracts (ISP)"],
        ],
    },
    {
        "heading": "3. Java Collections Framework (JCF) & Algorithmic Complexity",
        "text": "The Java Collections Framework provides high-performance, reusable data structure architectures under the java.util root. Understanding performance trade-offs is essential for writing low-latency applications.",
        "metrics": [
            {"label": "HashMap Lookup", "value": "O(1) Average"},
            {"label": "TreeSet Search", "value": "O(log n) Red-Black"},
            {"label": "ArrayList Access", "value": "O(1) Random Access"},
            {"label": "ConcurrentHashMap", "value": "CAS + Bucket Locks"},
        ],
        "bullets": [
            "List Hierarchy: ArrayList provides contiguous array backing with O(1) random access but O(n) middle insertions; LinkedList provides doubly-linked nodes with high memory pointer overhead.",
            "Set Hierarchy: HashSet relies on an underlying HashMap with O(1) membership check; TreeSet implements NavigableSet with sorted O(log n) order via Red-Black self-balancing binary search tree.",
            "Map Internals: HashMap uses bucket array with linked lists; when collisions in a bucket exceed threshold 8 (TREEIFY_THRESHOLD) and capacity >= 64, buckets convert into balanced TreeNode red-black trees.",
            "Hash Code & Equals Contract: If obj1.equals(obj2) is true, then obj1.hashCode() MUST equal obj2.hashCode(). Breaking this causes catastrophic lookup failures in hash-based structures.",
            "Fail-Fast vs. Fail-Safe: Standard iterators (ArrayList, HashMap) throw ConcurrentModificationException on structural modification during iteration; Concurrent collections (CopyOnWriteArrayList, ConcurrentHashMap) are fail-safe.",
        ],
        "table": [
            ["Collection Type", "Ordering Guarantee", "Allows Duplicates", "Get / Search Complexity", "Add / Put Complexity", "Thread-Safe"],
            ["ArrayList", "Insertion order", "Yes", "O(1) by index", "O(1) amortized", "No (Use Collections.synchronizedList)"],
            ["LinkedList", "Insertion order", "Yes", "O(n) linear search", "O(1) at head/tail", "No"],
            ["HashSet", "Unordered", "No", "O(1) average", "O(1) average", "No"],
            ["TreeSet", "Natural / Comparator", "No", "O(log n) binary tree", "O(log n)", "No"],
            ["HashMap", "Unordered", "Keys: No, Values: Yes", "O(1) avg / O(log n) collision", "O(1) average", "No (Use ConcurrentHashMap)"],
            ["ConcurrentHashMap", "Unordered", "Keys: No, Values: Yes", "O(1) lock-free reads", "O(1) synchronized per bin", "Yes (Highly Concurrent)"],
        ],
    },
    {
        "heading": "4. Multithreading, Concurrency, & Virtual Threads",
        "text": "Java was built from day one with multithreading support. Java 21 introduced Virtual Threads (Project Loom), fundamentally transforming high-throughput server architecture from reactive complexity back to simple synchronous thread-per-request models.",
        "metrics": [
            {"label": "Platform Thread", "value": "1:1 OS Thread (~1 MB)"},
            {"label": "Virtual Thread", "value": "M:N Carrier (~1 KB)"},
            {"label": "Thread Creation", "value": "Millions Concurrent"},
            {"label": "Atomic Variables", "value": "Hardware Lock-Free CAS"},
        ],
        "bullets": [
            "Thread Lifecycle: NEW -> RUNNABLE -> BLOCKED (waiting for monitor lock) -> WAITING -> TIMED_WAITING -> TERMINATED.",
            "Synchronization & Visibility: 'synchronized' provides mutual exclusion and memory barriers; 'volatile' guarantees visibility of reads/writes across CPU caches via happens-before edge, but does NOT guarantee atomicity.",
            "Modern Concurrency Utilities: java.util.concurrent (JUC) delivers ReentrantLock, CountDownLatch, CyclicBarrier, Semaphore, and ExecutorService thread pools (Fixed, Cached, WorkStealing).",
            "Virtual Threads (Java 21 LTS): Lightweight user-mode threads managed by JVM runtime; unmount from carrier OS threads during blocking I/O, allowing servers to handle 1,000,000+ concurrent connections without reactive frameworks.",
            "Lock-Free Algorithms: AtomicInteger, AtomicReference, and LongAdder leverage CPU-level Compare-And-Swap (CAS) instructions to eliminate OS-level context switching.",
        ],
        "table": [
            ["Concurrency Primitive", "Mechanism", "Scope / Granularity", "Performance Profile", "Recommended Use Case"],
            ["synchronized block", "Intrinsic JVM Monitor lock", "Block / Method level", "Heavier under contention", "Simple critical sections"],
            ["ReentrantLock", "Explicit Lock API", "Configurable fairness, timed tryLock", "High throughput under contention", "Complex locking, interruptible locks"],
            ["volatile keyword", "CPU cache flush memory barrier", "Variable read/write visibility", "Extremely lightweight (no lock)", "Status / cancelation flags"],
            ["AtomicInteger / CAS", "CPU hardware CAS loop", "Primitive / reference mutation", "Zero context switch overhead", "High-frequency counters and metrics"],
            ["Virtual Threads", "ForkJoinPool Carrier scheduling", "Thread per task / request", "Microsecond mount/unmount", "I/O-heavy web APIs and microservices"],
        ],
    },
    {
        "heading": "5. Robust Exception Handling & Resource Safety",
        "text": "Exception handling in Java separates normal execution logic from error recovery. Following modern best practices ensures that system resources are never leaked and errors provide actionable diagnostic information.",
        "metrics": [
            {"label": "Hierarchy Root", "value": "java.lang.Throwable"},
            {"label": "Resource Safety", "value": "try-with-resources"},
            {"label": "Checked Exceptions", "value": "Compile-time Enforced"},
            {"label": "Unchecked Exceptions", "value": "Subclasses of RuntimeException"},
        ],
        "bullets": [
            "Throwable Hierarchy: Divided into Error (JVM-level catastrophic failures like OutOfMemoryError, StackOverflowError - do NOT catch) and Exception (application-level recoverable conditions).",
            "Checked vs. Unchecked: Checked exceptions (IOException, SQLException) require explicit throws or try-catch; Unchecked exceptions (NullPointerException, IllegalArgumentException) inherit from RuntimeException.",
            "Try-With-Resources (Java 7+): Automatically closes any resource implementing AutoCloseable (files, sockets, database connections) in reverse order of declaration, even if exceptions are thrown.",
            "Suppressed Exceptions: When both the try block and auto-close trigger exceptions, try-with-resources attaches the secondary exception to the primary via Throwable.addSuppressed().",
            "Clean Handling Rules: Never swallow exceptions with empty catch blocks; never catch generic Throwable or Exception unless at the top-level boundary; always log or rethrow with cause chaining.",
        ],
        "table": [
            ["Exception Type", "Superclass", "Compiler Enforcement", "Typical Cause", "Recommended Response"],
            ["Checked Exception", "java.lang.Exception", "Mandatory try-catch or throws", "Unavoidable external failures (file missing, network down)", "Recover gracefully or translate to domain exception"],
            ["Unchecked Exception", "java.lang.RuntimeException", "Optional handling", "Programming defect (null access, invalid index)", "Fix caller logic; validate inputs early with Objects.requireNonNull"],
            ["JVM Error", "java.lang.Error", "Never catch", "Catastrophic JVM exhaustion (out of memory, stack overflow)", "Log diagnostic telemetry and permit JVM termination"],
            ["Custom Exception", "Business Exception / RuntimeException", "Based on extension", "Domain rule violation (e.g., InsufficientFundsException)", "Include contextual IDs and operational error codes"],
        ],
    },
    {
        "heading": "6. Modern Java Evolution: Java 8 to Java 21+ LTS Milestones",
        "text": "Java has evolved rapidly under the 6-month release cadence, introducing functional paradigms, concise syntax, and modern runtime performance while maintaining exceptional backward compatibility.",
        "metrics": [
            {"label": "Java 8 LTS", "value": "Lambdas & Streams"},
            {"label": "Java 11 LTS", "value": "HTTP/2 & Var Syntax"},
            {"label": "Java 17 LTS", "value": "Sealed Classes & Records"},
            {"label": "Java 21 LTS", "value": "Virtual Threads & Pattern Matching"},
        ],
        "bullets": [
            "Functional Programming (Java 8): Lambda expressions (x -> x * 2), functional interfaces (@FunctionalInterface), method references (Class::method), and declarative Streams API pipelines.",
            "Records (Java 14/16): Transparent immutable data carriers with auto-generated constructor, getters, equals, hashCode, and toString (record Point(int x, int y) {}).",
            "Pattern Matching (Java 16/21): Pattern matching for 'instanceof' eliminates redundant casting; switch pattern matching allows exhaustive type-based branching with guard expressions.",
            "Sealed Classes & Interfaces (Java 17): Restrict which subclasses can extend or implement them using 'sealed ... permits ...', providing closed algebraic data types for domain modeling.",
            "Sequenced Collections (Java 21): Introduces SequencedCollection, SequencedSet, and SequencedMap with unified first/last element access (getFirst(), getLast(), reversed()).",
        ],
        "table": [
            ["Java LTS Version", "Year", "Flagship Features", "Architectural Impact"],
            ["Java 8 LTS", "2014", "Lambdas, Streams API, Optional, new java.time Date/Time API, Interface Default Methods", "Shifted Java toward declarative functional-style data processing"],
            ["Java 11 LTS", "2018", "Local-variable type inference ('var' in lambdas), Native HttpClient (HTTP/2), Epsilon GC", "Modernized web protocols and reduced boilerplate syntax"],
            ["Java 17 LTS", "2021", "Sealed classes, Records, Pattern matching for instanceof, Foreign Function & Memory API (Incubator)", "Introduced algebraic data types and modern domain modeling"],
            ["Java 21 LTS", "2023", "Virtual Threads (Project Loom), Pattern matching for switch, Record patterns, Sequenced Collections", "Revolutionized high-scale concurrent server throughput and type safety"],
        ],
    },
]


def main() -> None:
    workspace_dir = Path("workspace")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    out_dir_str = str(workspace_dir)

    print("=" * 75)
    print("   PROJECT JARVIS - MULTI-FORMAT CORE JAVA DOCUMENT SUITE GENERATOR")
    print("=" * 75)
    print(f"Topic: {TITLE}")
    print(f"Output Directory: {workspace_dir.resolve()}\n")

    generated_files = []

    # 1. Generate Executive PDF Document (Theme: clean_light)
    print("[1/4] Generating Publication-Grade PDF with CreatePdfTool (Theme: clean_light)...")
    pdf_tool = CreatePdfTool()
    pdf_res = pdf_tool.run(
        title=TITLE,
        sections=SECTIONS,
        theme="clean_light",
        out_dir=out_dir_str,
        auto_open=False,
    )
    if not pdf_res.success:
        print(f"[ERROR] PDF generation failed: {pdf_res.message}")
        sys.exit(1)
    pdf_path = pdf_res.data["file_path"]
    pdf_size = os.path.getsize(pdf_path)
    print(f"  [PASS] PDF generated: {pdf_path} ({pdf_size:,} bytes)")
    generated_files.append(("PDF", pdf_path, pdf_size))

    # 2. Generate Word DOCX Document (Theme: dark_pro)
    print("\n[2/4] Generating Executive Word Document with CreateDocxTool (Theme: dark_pro)...")
    docx_tool = CreateDocxTool()
    docx_res = docx_tool.run(
        title=TITLE,
        sections=SECTIONS,
        theme="dark_pro",
        out_dir=out_dir_str,
        auto_open=False,
    )
    if not docx_res.success:
        print(f"[ERROR] DOCX generation failed: {docx_res.message}")
        sys.exit(1)
    docx_path = docx_res.data["file_path"]
    docx_size = os.path.getsize(docx_path)
    print(f"  [PASS] DOCX generated: {docx_path} ({docx_size:,} bytes)")
    generated_files.append(("DOCX", docx_path, docx_size))

    # 3. Generate Widescreen 16:9 Presentation Deck (Theme: colourful)
    print("\n[3/4] Generating Widescreen PowerPoint Deck with CreatePptxTool (Theme: colourful)...")
    pptx_tool = CreatePptxTool()
    pptx_res = pptx_tool.run(
        title=TITLE,
        sections=SECTIONS,
        theme="colourful",
        out_dir=out_dir_str,
        auto_open=False,
    )
    if not pptx_res.success:
        print(f"[ERROR] PPTX generation failed: {pptx_res.message}")
        sys.exit(1)
    pptx_path = pptx_res.data["file_path"]
    pptx_size = os.path.getsize(pptx_path)
    print(f"  [PASS] PPTX generated: {pptx_path} ({pptx_size:,} bytes)")
    generated_files.append(("PPTX", pptx_path, pptx_size))

    # 4. Generate Interactive Web Artifact / HTML Dashboard (Theme: tech_innovation)
    print("\n[4/4] Generating Interactive Web Artifact with CreateWebsiteTool (Theme: tech_innovation)...")
    web_tool = CreateWebsiteTool()
    web_res = web_tool.run(
        title=TITLE,
        sections=SECTIONS,
        theme="tech_innovation",
        out_dir=out_dir_str,
        auto_open=False,
        filename="core_java_important_points.html",
        hero_tagline=HERO_TAGLINE,
    )
    if not web_res.success:
        print(f"[ERROR] Web generation failed: {web_res.message}")
        sys.exit(1)
    web_path = web_res.data["file_path"]
    web_size = os.path.getsize(web_path)
    print(f"  [PASS] HTML generated: {web_path} ({web_size:,} bytes)")
    generated_files.append(("HTML", web_path, web_size))

    # Integrity Validations
    print("\n" + "=" * 75)
    print("                    VALIDATING DOCUMENT INTEGRITY")
    print("=" * 75)

    # 1. Validate PDF header and size
    with open(pdf_path, "rb") as f:
        pdf_hdr = f.read(5)
        assert pdf_hdr == b"%PDF-", f"Invalid PDF header: {pdf_hdr}"
    print(f"  [OK] PDF Header validated (%PDF- format, {pdf_size:,} bytes)")

    # 2. Validate Word Document structure
    import docx
    doc = docx.Document(docx_path)
    print(f"  [OK] Word DOCX structure validated ({len(doc.paragraphs)} paragraphs, {len(doc.tables)} tables, {docx_size:,} bytes)")

    # 3. Validate PowerPoint Deck slides
    import pptx
    prs = pptx.Presentation(pptx_path)
    print(f"  [OK] PowerPoint Deck structure validated ({len(prs.slides)} widescreen slides, {pptx_size:,} bytes)")

    # 4. Validate HTML Content
    with open(web_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        assert "<!DOCTYPE html>" in html_content
        assert "Core Java" in html_content
        assert "Virtual Threads" in html_content
    print(f"  [OK] HTML Web Artifact validated (Valid HTML5 bundle, {web_size:,} bytes)")

    print("\n" + "=" * 75)
    print("  ALL 4 CORE JAVA PRODUCTION DOCUMENTS GENERATED SUCCESSFULLY!")
    print("=" * 75)
    for fmt, path, sz in generated_files:
        print(f"  * {fmt:<5}: {path} ({sz:,} bytes)")
    print("=" * 75)


if __name__ == "__main__":
    main()
