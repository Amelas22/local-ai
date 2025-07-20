# 8. Migration and Optimization

[← Previous: Example Legal Agents](07-example-agents.md) | [Back to Overview →](00-overview.md)

---

## Migration Assessment Guide

### Identifying Migration Candidates

```python
class MigrationAssessment:
    def assess_agent_for_migration(self, existing_agent: str) -> dict:
        """Assess existing agent for BMad migration."""
        
        assessment = {
            "agent_name": existing_agent,
            "migration_score": 0,
            "benefits": [],
            "risks": [],
            "effort_estimate": 0
        }
        
        # Check complexity
        if self.has_complex_workflows(existing_agent):
            assessment["benefits"].append("Better workflow management")
            assessment["migration_score"] += 20
            
        # Check maintenance burden
        if self.high_maintenance_cost(existing_agent):
            assessment["benefits"].append("Reduced maintenance")
            assessment["migration_score"] += 30
            
        # Check reusability potential
        if self.low_reusability(existing_agent):
            assessment["benefits"].append("Increased reusability")
            assessment["migration_score"] += 25
            
        return assessment
```

### Cost-Benefit Analysis

```markdown
## Migration Cost-Benefit Template

### Agent: [AGENT_NAME]

#### Benefits
- [ ] Declarative configuration (easier maintenance)
- [ ] Standardized patterns (reduced learning curve)
- [ ] Built-in elicitation support
- [ ] Automatic API mapping
- [ ] WebSocket progress tracking
- [ ] Better testability

#### Costs
- [ ] Migration effort: [X] hours
- [ ] Testing effort: [Y] hours  
- [ ] Documentation update: [Z] hours
- [ ] Team training: [W] hours

#### Risk Assessment
- Data migration complexity: Low|Medium|High
- Business continuity impact: Low|Medium|High
- Rollback complexity: Low|Medium|High

#### Recommendation
Migrate if: Benefits > Costs * 1.5
```

### Risk Assessment Checklist

- [ ] **Data Compatibility**: Will existing data work with new format?
- [ ] **API Compatibility**: Are API contracts maintained?
- [ ] **Performance Impact**: Will migration affect response times?
- [ ] **Feature Parity**: Are all features preserved?
- [ ] **Integration Points**: Will integrations continue to work?
- [ ] **Security Model**: Is security model compatible?
- [ ] **Rollback Plan**: Can we quickly revert if needed?

## Migration Process

### Step-by-Step Conversion

```bash
# 1. Analyze existing agent
python analyze_agent.py --agent legal_document_agent.py

# 2. Generate BMad template
python generate_bmad_template.py \
  --from legal_document_agent.py \
  --to agents/document-generator.yaml

# 3. Map functions to tasks
python map_functions_to_tasks.py \
  --agent legal_document_agent.py \
  --output tasks/

# 4. Create templates from outputs
python extract_templates.py \
  --agent legal_document_agent.py \
  --output templates/

# 5. Validate migration
python validate_migration.py \
  --original legal_document_agent.py \
  --bmad agents/document-generator.yaml
```

### Testing Requirements

```python
class MigrationTester:
    async def test_migration(self, original: str, migrated: str):
        """Comprehensive migration testing."""
        
        # 1. Functional equivalence
        test_cases = self.load_test_cases(original)
        for test in test_cases:
            original_result = await self.run_original(test)
            migrated_result = await self.run_migrated(test)
            assert original_result == migrated_result
            
        # 2. Performance comparison
        perf_original = await self.benchmark(original)
        perf_migrated = await self.benchmark(migrated)
        assert perf_migrated.avg_time <= perf_original.avg_time * 1.1
        
        # 3. API compatibility
        api_tests = self.generate_api_tests(original)
        for test in api_tests:
            assert await self.test_api_compatibility(test)
```

### Rollback Procedures

```yaml
rollback_plan:
  preparation:
    - Tag current version before migration
    - Backup all configuration
    - Document rollback triggers
    
  triggers:
    - Error rate > 5%
    - Response time > 2x baseline
    - Critical feature failure
    
  steps:
    - Stop new traffic to migrated agent
    - Route to original agent
    - Investigate issues
    - Fix and re-test
    
  validation:
    - Verify original functionality
    - Check data integrity
    - Monitor for 24 hours
```

### Parallel Running

```python
class ParallelRunner:
    async def run_parallel(self, request: dict, config: dict):
        """Run both agents in parallel for comparison."""
        
        # Route percentage to new agent
        if random.random() < config["canary_percentage"]:
            # Run new agent
            result = await self.run_bmad_agent(request)
            
            # Shadow run old agent for comparison
            if config["shadow_mode"]:
                old_result = await self.run_original_agent(request)
                await self.compare_results(result, old_result)
                
            return result
        else:
            # Run original agent
            return await self.run_original_agent(request)
```

## Performance Guide

### Profiling Agent Performance

```python
from bmad_framework.profiler import AgentProfiler

profiler = AgentProfiler()

# Profile command execution
with profiler.profile("analyze_command"):
    result = await executor.execute_command(
        agent_def=agent,
        command="analyze",
        case_name="Test_Case"
    )

# Get performance report
report = profiler.get_report()
print(f"Total time: {report.total_time}ms")
print(f"Task loading: {report.task_loading_time}ms")
print(f"Execution: {report.execution_time}ms")
print(f"Memory peak: {report.peak_memory}MB")
```

### Optimization Techniques

```python
# 1. Dependency Caching
class OptimizedLoader:
    def __init__(self):
        self._cache = LRUCache(maxsize=100)
        
    async def load_dependency(self, dep: str):
        if dep in self._cache:
            return self._cache[dep]
        
        content = await self.read_file(dep)
        self._cache[dep] = content
        return content

# 2. Parallel Task Execution
async def execute_parallel_tasks(tasks: List[str]):
    """Execute independent tasks in parallel."""
    results = await asyncio.gather(*[
        execute_task(task) for task in tasks
    ])
    return results

# 3. Lazy Loading
class LazyDependencyLoader:
    def __getattr__(self, name: str):
        """Load dependencies only when accessed."""
        if name not in self._loaded:
            self._loaded[name] = self.load_dependency(name)
        return self._loaded[name]
```

### Resource Management

```yaml
resource_limits:
  memory:
    max_agent_memory: 500MB
    cache_size: 100MB
    
  cpu:
    max_concurrent_tasks: 5
    task_timeout: 300s
    
  io:
    max_file_handles: 50
    connection_pool_size: 20
    
monitoring:
  metrics:
    - memory_usage
    - cpu_utilization
    - response_time
    - error_rate
    
  alerts:
    - memory_usage > 80%
    - response_time > 5s
    - error_rate > 1%
```

### Scaling Considerations

```python
class ScalableAgentExecutor:
    def __init__(self, config: dict):
        self.worker_pool = WorkerPool(
            min_workers=config["min_workers"],
            max_workers=config["max_workers"]
        )
        self.rate_limiter = RateLimiter(
            requests_per_second=config["rate_limit"]
        )
        
    async def execute_at_scale(self, requests: List[dict]):
        """Execute multiple requests with scaling."""
        
        # Apply rate limiting
        async with self.rate_limiter:
            # Distribute to workers
            results = await self.worker_pool.map(
                self.execute_single,
                requests
            )
            
        return results
```

---

## Conclusion

This guide provides comprehensive coverage of the BMad Legal AI Agent Framework lifecycle. Key takeaways:

1. **Creation**: Use structured approach with planning before implementation
2. **Definition**: Follow YAML conventions for consistency
3. **Activation**: Understand the loading and persona adoption process
4. **Utilization**: Leverage command patterns and state management
5. **Best Practices**: Apply BMad patterns consistently
6. **Migration**: Assess carefully and test thoroughly
7. **Optimization**: Profile and optimize for production use

For additional support, refer to:
- Example agents in `bmad-framework/agents/`
- Task library in `bmad-framework/tasks/`
- Template collection in `bmad-framework/templates/`
- Test suite in `bmad-framework/tests/`

---

[← Previous: Example Legal Agents](07-example-agents.md) | [Back to Overview →](00-overview.md)