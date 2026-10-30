# HUMANS.md 研究 コードブック v1 校正シート(人間2名用)

- 記入者: ______________  記入日: ______________
- 先に `work/codebook/codebook_v1.md` の「判定手順」と「境界例」を読んでください(実例の sid はこのシートと重なることがあるが、その件の正解とは限らない)。
- 2名は**相談せずに独立に**記入してください。結末(マージ/クローズ)・作者が AI か人間か・既存ラベルは伏せてあります。本文中の `@copilot` などから推測できる場合もありますが、推測した事実は判定に使わないでください。
- 「文書確認」のリンクは PR の base commit 時点のリポジトリです。README / CONTRIBUTING / AGENTS.md / .github/copilot-instructions.md / CLAUDE.md を見て「既に書かれていたか」を判定してください(1件 3 分まで。見つからなければ「書かれていない」で可)。PR ページは結末が見えるので開かないでください。

記入欄:
- **主**: X / C1 / C2 / C3 / M / K-pub / K-priv / R-tech / R-gov / D-dir / D-risk / UNK のどれか1つ
- **副**: 同じ選択肢から0〜1個(なければ空欄)
- **書けたか**: could(事前に一般的な文として書けた)/ no(その場でしか出ない)/ -(C・X・UNK)
- **書かれていたか**: yes / partial / no / 見られない(K・R・D のときだけ)
- **確信度**: 1(迷った)〜 3(迷わない)

## Q01  microsoft/PSRule | Add hot reload support for PSRule options with VS Code configuration synchronization

文書確認: https://github.com/microsoft/PSRule/tree/37aca60781ca8bc3378c643e90578b0dc5cb0647

**レビュー本文**: (なし)
- `[client.ts]` @copilot If option `PSRule.options.path` is set, watch that file, otherwise default to watching `ps-rule.yaml`.  Don't include the other variations e.g. `ps-rule.yml`, `psrule.yaml` or `ps-rule.yml`.
- `[WorkspaceChangeWatcherHandler.cs]` @copilot If option `PSRule.options.path` is set, watch that file, otherwise default to watching `ps-rule.yaml`.  Don't include the other variations e.g. `ps-rule.yml`, `psrule.yaml` or `ps-rule.yml`.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q02  microsoft/vscode-azurefunctions | Upgrade TypeScript devDependency to ^5.9.2

文書確認: https://github.com/microsoft/vscode-azurefunctions/tree/3bb06ae07586b168aa4881fea49d9a9755854def

**レビュー本文**: Abandoning this pending review as requested.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q03  apache/airflow | Add option to override Celery worker images

文書確認: https://github.com/apache/airflow/tree/7b29d3b02ab1323eb26304a7debe8935f7aa76a2

**レビュー本文**: Overall, this is a nice change that aligns with the Workers Sets feature. Let's wait a bit and revisit it in the next round after some discussions on the Helm Chart releases (the images section and design of it are one of the action items) are finished.
- `[_helpers.yaml]` Most of this function copies logic from `airflow_image`. Maybe there is some nice way to not duplicate code here?
- `[values.yaml]` ```suggestion ``` Not sure if needed. Every section can be overwritten by sets and direct message for one field could lead to `this has this information and other field do not, so I can overwrite this one but this one not?` understanding.
- `[test_worker_image.py]` This added test complexity, which can lead to not-so-straightforward debugging in case of failure. Maybe we could simplify the test cases a little?
- `[test_worker_image.py]` Not sure where the `images` section tests are stored, but I think we should move them there to have all `images` test in one place.
- `[test_worker_image.py]` All of the tests regarding `celery` overwrite `workers` are in the general worker test file. Could we move those tests there?
- `[test_worker_image.py]` All of the tests for `sets` overwrite of `celery`, and the `workers` section is in the workers sets dedicated test file. Could we move these tests there?

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q04  swc-project/swc | feat(es/minifier): Implement parameter inlining optimization

文書確認: https://github.com/swc-project/swc/tree/94f175d643f38477d2c84f00c8602bfebdb7b343

**レビュー本文**: Run `UPDATE=1 cargo test -p swc --test tsc --test projects` and `UPDATE=1 cargo test -p swc_ecma_minifier`

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q05  1c-syntax/bsl-language-server | Fix ClassCastException in MagicNumberDiagnostic with soft error handling

文書確認: https://github.com/1c-syntax/bsl-language-server/tree/6957f42875322d2cc55e11f10fe1816a298b9643

**レビュー本文**: (なし)
- `[DiagnosticParameterValidator.java]` нужен javadoc на класс
- `[DiagnosticParameterValidator.java]` используй `@Getter(lazy = true)`
- `[DiagnosticParameterValidator.java]` промаркируй его как @Nullable, раз оно может быть null даже при отложенной инициализации

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q06  espressif/arduino-esp32 | fix(logging): Add wrapper when using wifi without esp_diagnostics

文書確認: https://github.com/espressif/arduino-esp32/tree/11bc7ac1a458f1f4e7afc8fd4de1dfa710f31562

**レビュー本文**: @lucasssvaz - I think that it would be good to add `DIAG_USE_EXTERNAL_LOG_WRAP` to the KConfig file (https://github.com/espressif/arduino-esp32/blob/master/Kconfig.projbuild).  Not sure which would be the best default value for it. Please evalutate it.  In case its default value is `y`, you may just remove it from `sdkconfig.defaults` file

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q07  firecrawl/firecrawl | fix: replace hardcoded search billing with calculateCreditsToBeBilled

文書確認: https://github.com/firecrawl/firecrawl/tree/b5b6ca0a322353498b41ecf619399dd718f21c0d

**レビュー本文**: (なし)
- `[search.ts]` rework so that scrapeSearchResult returns a costTracking for each document, and each separate costTracking is utilized to calculate a separate price for each document, which is then summed

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q08  Azure/azure-sdk-for-rust | Add tests to demonstrate etag deserialization issue in BlobPropertiesInternal struct

文書確認: https://github.com/Azure/azure-sdk-for-rust/tree/91d0b563baf7132392faaac6c8577f62c4e6ec7f

**レビュー本文**: @copilot you must not change files under the "generated" folder. These changes must be made in the TypeSpec.  @vincenttran-msft @seanmck are these changes queued up for your TypeSpec?

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q09  apache/airflow | Don't provide default values for PDBs in chart.

文書確認: https://github.com/apache/airflow/tree/6f79705b3723fcc9d2e1309a9371c259b74a454c

**レビュー本文**: For me it seems more like a bug, so should we make sure that it works for previous versions where it was a bug? I would say, not necessarily, but I would ask for a second opinion - @jscheffl, @jedcunningham WDYT?  \+ @simi I think we should add newsfragment for it
- `[test_pdb_apiserver.py]` According to the Helm Chart docs we support k8s >= 1.30, so I guess we can delete that test

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q10  ray-project/ray | [data.llm] Add release test to capture memory leak

文書確認: https://github.com/ray-project/ray/tree/57125ad231f0ee6c9fd7c869c809c07a5b5ebd68

**レビュー本文**: the customer face memory issues with using 4 nodes with each node has a single gpu, so we should use that in the compute config as the test

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q11  ydb-platform/ydb | Add CI check for error_tags

文書確認: https://github.com/ydb-platform/ydb/tree/bf608a2629f4e733fa349dcd1f733f9c5c19c041

**レビュー本文**: (なし)
- `[error_tags_check.yml]` `error_tags_check.yml` не перезапускается при добавлении `ok-to-test`, в отличие от `pr_check.yml`.  В `pr_check` явно указано:  ```yaml types:   - opened   - synchronize   - reopened   - labeled ```  В `error_tags_check` — только дефолтные события (`opened`, `synchronize`, `reopened`), без `labeled`.  **Что ломается:** для внешнего контрибьютора workflow стартует на `opened`, ownership check возвращает `false`, валидация skip'ается. Maintainer ставит `ok-to-test` → `pr_check` сразу перезапускается, а `error_tags_check` — нет, пока автор не сделает новый push.  **Предложение:** добавить `labeled` в `on.pull_request_target.types` (и по аналогии с `pr_check` — concurrency/условие, чтобы irrelevant labels не отменяли running checks).

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q12  goauthentik/authentik | website/docs: add password lockout 2026.11 release notes

文書確認: https://github.com/goauthentik/authentik/tree/6fb387b56e7821b43ba9b3c0c25567adc5b3b863

**レビュー本文**: (なし)
- `[v2026.11.md]` ```suggestion - **User status**: The user list in the Admin interface shows a single consolidated status for each user, indicating whether the account is active, deactivated, or password locked. ```
- `[v2026.11.md]` ```suggestion The [Password stage](../../add-secure-apps/flows-stages/stages/password/index.md#password-lockout) can now lock a user's password after a set number of consecutive failed attempts, using the new **Failed attempts before lockout** option. This is disabled by default. ```
- `[v2026.11.md]` ```suggestion When a user account is password locked, authentication is denied even if the correct password is entered. This prevents further guessing attempts and blocks use of a compromised password until an administrator unlocks it. The attempt count is tracked per user, retained across sessions and authentication flows, and cleared after a successful login. ```
- `[v2026.11.md]` ```suggestion The login prompt returns the same error as it does for an incorrect password, preventing it from disclosing whether an account exists or is password locked. Password lock and unlock actions are logged as `password_locked` and `password_unlocked` events. ```
- `[v2026.11.md]` ```suggestion Administrators can unlock a user's account from that user's page in the Admin interface. Changing the password also clears the lock, so a password reset is always a way to regain access. ```

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q13  backstage/backstage | fix(ui): Hide browser-specific password field controls in PasswordField

文書確認: https://github.com/backstage/backstage/tree/2043706d2452fd795fa14f83d07aaf517ad07162

**レビュー本文**: Keeping browser specific password manager controls intact seems like a useful feature, to allow users to use these tools for creating and managing the passwords.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q14  dotnet/msbuild | Track subclasses of MSBuild tasks for telemetry

文書確認: https://github.com/dotnet/msbuild/tree/044c796561d5c06be5c8caeac8a7bf0334e4232d

**レビュー本文**: (なし)
- `[ProjectTelemetry.cs]` @copilot you need to check the entire inheritance heirarchy, not just the first level
- `[ProjectTelemetry.cs]` @copilot rename this event - it's not about 'microsoft tasks' per se - it's about MSBuild tasks specifically. And I want to change the shape of the data we're collecting.  I want to track the usage of non-sealed Microsoft-owned Tasks specifically. So let's keep a dictionary of Microsoft Task Names to counts of their non-sealed usage. We should inspect every Task, and if it is a subclass of a MIcrosoft-owned Task, we should track the name of that Microsoft-owned Task and increment the usage count. The final telemetry emitted should be a mapping of Microsoft-owned task names to counts of their non-sealed usage.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q15  compas-dev/compas | Add optional units and uncertainties support with comprehensive geometry integration

文書確認: https://github.com/compas-dev/compas/tree/b8cef0dd8797c05228207f6ce9d2e688bb9c6864

**レビュー本文**: @copilot the ironpython tests are still failing. Just ignore them but not with the `skipif`, instead do `if not compas.IPY:` to ignore

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q16  microsoft/vscode-pull-request-github | Fix wrong commit checkout when local branch exists with same name as PR

文書確認: https://github.com/microsoft/vscode-pull-request-github/tree/8bb9fd88e5a204c762e43f49e2d579ec42bb9177

**レビュー本文**: (なし)
- `[pullRequestGitHelper.ts]` @copilot This is dangerous. We shouldn't just delete the user's local branch. Instead, we should create a local branch with a different, available, name, and point the branch's remote to the correct upstream branch.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q17  tgstation/tgstation | The Torment Nexus: The future of Security brigging and prisoner rehabilitation! FEAT. Baton Skin Crates

文書確認: https://github.com/tgstation/tgstation/tree/f46777aad3a97455ac057f9d06d36636093e2a33

**レビュー本文**: (なし)
- `[loot_crate.dm]` Let me get this straight:  1. Security now has a way to infinity farm frag grenades and laser guns for themselves, at no cost or interaction with cargo, in their down time  and  2. Initially this started as an alternative to brigging with no incentive, meaning it was ultimately up to the security officer (and the prisoner, to a lesser degree) whether they wanted to be subjected to this - but now security is incentivized to _never_ use the normal brig, because they are not receiving (incredibly lucrative!) passive rewards    Nooooooo, no. No gun or tool rewards in this. You can make it money that gets deposited in the security budget or resources or something.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q18  ceph/ceph | Add pre-upgrade validation for health/OSDs/PGs

文書確認: https://github.com/ceph/ceph/tree/4f9a9b5f2d479e16e6b0ff058fad5954367ce76c

**レビュー本文**: We cannot merge upgrade-breaking regressions, even temporarily.
- `[upgrade.py]` I appreciate the capabilities this PR adds, but as @JoshuaGabriel noted, requiring all OSDs be up+in is a mega-regression. (For one thing, if an osd is down due to a bug, you can’t upgrade to fix it!) I don’t believe we can merge this PR as it stands.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q19  SigNoz/signoz | feat: handle conflicting attributes with data type and context-based resolution

文書確認: https://github.com/SigNoz/signoz/tree/44f00943a8ffe8ca498ba6bc52531a3ec45c4a5e

**レビュー本文**: Logic introduced to differentiate options based on keys has complications which could have been avoided. Since this has a huge blast radius we should not go ahead with this solution.
- `[utils.tsx]` This is getting calculated for every columnName which is expensive and can be avoided.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q20  gradle/gradle | Document that @InputFiles is order-insensitive

文書確認: https://github.com/gradle/gradle/tree/a42f1f576913f31a1104cfc6131e165cb19e26a1

**レビュー本文**: Thank you for your proposed contribution!  This PR has a valid DCO and is documentation only.  ***  Before it can be merged, please address the review comments below.
- `[InputFiles.java]` ❌ The reference to `Classpath` should be moved to a `@see` instead, as it indeed provides order dependence but does more. And `InputDirectory` can also be moved to `@see`  💅 Please put each sentence on a newline as shown in [our guide](https://github.com/gradle/gradle/blob/master/contributing/JavadocStyleGuide.md).

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q21  dotnet/sdk | Suppress CS8002 warning for modern .NET TFMs

文書確認: https://github.com/dotnet/sdk/tree/51297ba882a9da20765f0f5ca468523bc6d4ce12

**レビュー本文**: (なし)
- `[Microsoft.NET.Sdk.CSharp.targets]` CS8002 must not be automatically suppressed when targeting .NET Standard 2.0 or lower.  Assemblies that were built targeting those frameworks can be run on .NET Framework, which still checks strong names, so the warnings are justified.  When targeting .NET Standard 2.1, CS8002 could in principle be suppressed because no version of .NET Framework supports .NET Standard 2.1.  However, I recommend that the SDK not suppress CS8002 on any version of .NET Standard, because this will be easier for users to understand.  There is hardly any reason to target .NET Standard 2.1 nowadays anyway.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q22  celestiaorg/celestia-app | docs: Add v4 release notes with message changes

文書確認: https://github.com/celestiaorg/celestia-app/tree/8d6a2fc2d384ec37150117927ef908495e74c457

**レビュー本文**: overall this feels very repetitive  be more concise. if a change impacted apis and imports etc, just mention that instead of having separate sections mentioning the same exact thing
- `[release-notes.md]` also mention the change from CometBFT v0.34 -> v0.38
- `[release-notes.md]` ```suggestion **IBC Protocol Update (v6 → v8)**: ```
- `[release-notes.md]` please double check these and only include them if something changed. if something did change, then only mention that
- `[release-notes.md]` ```suggestion ```  I think we can delete these
- `[release-notes.md]` does this include all api changes? what about to `TxClient` or the user package?

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q23  dotnet/runtime | Handle BadImageFormatException in OpenAssociatedSymbolFile

文書確認: https://github.com/dotnet/runtime/tree/93df345b3188c2d0c413bfdf1cafbdb47de752a5

**レビュー本文**: Why do we want to mask this error? It does not look right to me. Our general strategy in AOT compilers is to fail the compilation when the input is malformed. It is expected that the malformed input can and will cause the compiler to crash or fail  The error in the issue is either a race condition in the build where the build is overwriting the compiler inputs, or it is a memory corruption (e.g. GC hole) leading to intermittent crash.  We need to get a crash dump of the failure to tell. It is a long outstanding problem that the builds are not producing crash dumps that made investigation of many issues difficult/impossible.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q24  open-telemetry/opentelemetry-collector-contrib | [pkg/stanza] Fix writer error propagation and add helper tests

文書確認: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/c44528c7190333ec52d3c7f969cc84d66d740770

**レビュー本文**: This change looks like AI slop to me.  The behavior of `ProcessBatch` mirrors the behavior of `Process`. The decision to only return the error from the last operator was made deliberately in https://github.com/open-telemetry/opentelemetry-collector-contrib/pull/34342.  If you think it's incorrect, please create an issue describing the failure scenario in detail, including a minimal reproduction configuration, expected and actual result.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q25  apache/airflow | Google: Fix false success in Cloud Composer DAG run sensor

文書確認: https://github.com/apache/airflow/tree/7348e09bed647795ac05f9236840076a04bf7023

**レビュー本文**: This PR looks similar to this one https://github.com/apache/airflow/pull/61046 which was reverted because this code broke `CloudComposerDAGRunSensor`. Could you run the existing System Test for this operator and shared the screenshot for the latest run?

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q26  mgechev/revive | Add support for disabling specific struct-tag checkers

文書確認: https://github.com/mgechev/revive/tree/0dbaa8ccb4f3671cccea63b6048a5ac0156ef3df

**レビュー本文**: The configuration approach avoids configuring `disabled` as a custom option for a tag.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q27  ghostty-org/ghostty | fix(vt): forward UTF-8 bytes through DCS passthrough

文書確認: https://github.com/ghostty-org/ghostty/tree/472b926a4d7abbacad4deea17aa0a0c69ffc12d3

**レビュー本文**: I still approve this but going to put a block on merge until 1.3 is out the door, I don't want to risk something in the core parse table for 1.3.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q28  deepmodeling/deepmd-kit | chore: Clarify CPU-specific thread warning

文書確認: https://github.com/deepmodeling/deepmd-kit/tree/3f0087b48d8a3beb45a4703ca94c73acee97ba73

**レビュー本文**: #1284 shows that setting `OMP_NUM_THREADS` is still meaningful in the GPU training. I am wondering why we dismiss the warning.
- `[env.py]` ```suggestion     if use_cpu and ( ```
- `[env.py]` I don't think this environment variable is used in the TensorFlow backend.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q29  dotnet/runtime | [Wasm RyuJit] fix issue in RewriteLocalStackStore

文書確認: https://github.com/dotnet/runtime/tree/d6ea4621a9805436aa33f110f0ec67267619fcd2

**レビュー本文**: One question about the `TypeIs` check immediately after `ChangeType`

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q30  hi-ogawa/vite-plugins | feat(fullstack): add virtual:fullstack/no-split-css module for simplified CSS collection

文書確認: https://github.com/hi-ogawa/vite-plugins/tree/9a0f4ab9f8e8c4baf02ac3c377e4b093a3db8389

**レビュー本文**: @copilot It should not be dev only. Explore what this means for build to work to simplify server css integration.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q31  microsoft/mssql-python | FIX: Contribution process for internal/external contributors & documentation

文書確認: https://github.com/microsoft/mssql-python/tree/de72919316d25773e3ed991d1d121cbb560b3c72

**レビュー本文**: (なし)
- `[PULL_REQUEST_TEMPLATE.MD]` can link the GH issue using just a hashtag (#)
- `[PULL_REQUEST_TEMPLATE.MD]` Can use a better term here. something like `mssql-python` maintainers
- `[PULL_REQUEST_TEMPLATE.MD]` Can use a better term here. something like mssql-python maintainers

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q32  doodlum/skyrim-community-shaders | perf: cache GetRuntimeData usage for improved performance

文書確認: (リポジトリにアクセスできない)

**レビュー本文**: Please handle other similar examples you identified.  Is this something that should be implemented in our commonlib dependency or is this a client application issue?  Also, is this approach developer friendly?

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q33  nanvix/nanvix | [ci] Re-Structure Nanvix-Bench Results: Organize by Benchmark Instead of Machine Type

文書確認: https://github.com/nanvix/nanvix/tree/3320c8e9c414f7cc4a7ccbb6f17c8bb706e35e62

**レビュー本文**: @copilot make sure the "|" characters in the last column are aligned with the "|" character of the header.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q34  open-telemetry/opentelemetry-collector-contrib | [processor/schema] Add cache_ttl configuration option for in-memory schema cache

文書確認: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/b58b76dc34b551e6b4a7dc27466fb8400c13217f

**レビュー本文**: I am going to say that having a ttl cache is overkill here considering that schemas are immutable, and invalidating the cache here is going to cause either another disk read, or http request would can be costly when multiplied by several thousand deployed instances.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q35  SigNoz/signoz | Feat/migrate signup page to signoz UI 10615

文書確認: https://github.com/SigNoz/signoz/tree/b5c146afdfe0e6b8a5e5a78963c8f695d156cf3a

**レビュー本文**: Few changes related to styling
- `[SignUp.tsx]` Move to children, the message is being cut due to the title have the config of ellipsis
- `[SignUp.tsx]` Move to children, the message is being cut due to the title have the config of ellipsis
- `[SignUp.tsx]` Can be replaced to `Input.Password`.
- `[SignUp.tsx]` You can remove the CSS of the inputs and keep it without any CSS since it will look better.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q36  python/cpython | gh-146475: Block Apple LLVM 21 from passing JIT tool version check

文書確認: https://github.com/python/cpython/tree/5c0dcb3e0d817bd8c28e8efcdb97103cd9210989

**レビュー本文**: Based on earlier convos, I think this is mergeable with the amendment to the blurb and the regex.   @ashutoshk314 Friendly reminder to sign the CLA when you get a chance as we can't merge without it.
- `[2026-03-26-23-40-21.gh-issue-146475.F9KMLP.rst]` ```suggestion Block Apple Clang from being used to build the JIT as it ships without  required LLVM tools. ``` While the CFI directives are an issue, let's make this fix more about the underlying toolchain incompatibility (i.e. users have to install llvm-readobj still)

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q37  microsoft/genaiscript | Add streamlined GenAIScript cheat sheet focusing on core functionality

文書確認: https://github.com/microsoft/genaiscript/tree/34bdb01dbe872d04f74b5cf736670eab3c8ff161

**レビュー本文**: (なし)
- `[cheat-sheet.mdx]` Not correct, you don't access environment variables through env.vars @copilot
- `[cheat-sheet.mdx]` Remove section @copilot
- `[cheat-sheet.mdx]` Move this section much earlier, super important @copilot

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q38  collinbarrett/FilterLists | Split GameIndustry hosts into separate FilterList entries for each template variant

文書確認: https://github.com/collinbarrett/FilterLists/tree/3626340fb94d94d01714ebd18702257150f9639e

**レビュー本文**: @copilot , multiple FilterListViewUrls for a single FilterList are intended to be used if there are multiple mirrors of the same list or if the same list is broken into multiple parts per this wiki: https://github.com/collinbarrett/FilterLists/wiki/FilterListViewUrl  In this case, these are different "flavors" of the same list, so let's give each one their own entry in FilterList.json and all the related entities/.json files as well.  Capture this design in copilot-instructions.md as well so you remember that in the future.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q39  DefinitelyTyped/DefinitelyTyped | toastify-js, add the ESM module

文書確認: https://github.com/DefinitelyTyped/DefinitelyTyped/tree/9a869f9f8ae75b28cc865e36b95539a8ab42295a

**レビュー本文**: Requesting changes so the bot understands the current state.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q40  pytorch/pytorch | [torchgen] Refactor and simplify `gen_pyi.py` to use Generic TypeAlias (PEP 585) and Union Type (PEP 604)

文書確認: https://github.com/pytorch/pytorch/tree/672a3367855a1b689df2b85fb5cbe148e6ebd68b

**レビュー本文**: Unfortunately PEP604 is python 3.10+ and we have to support python 3.9 - so we can't convert to it yet.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q41  bugsink/bugsink | Add remote_addr field to Event model to log client IP addresses

文書確認: https://github.com/bugsink/bugsink/tree/6a80fe264a42233c08e845178bb2aa4feae16322

**レビュー本文**: (なし)
- `[models.py]` Overly verbose; drop the whole comment
- `[tests.py]` that's a lot of testing for very little functionality, which gives me a "bad feeling" generally and esp. since it was done by a bot.  could we not have a "tighter fit" around what's actually happening?

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q42  milkshakesoftware/PreMailer.Net | Fix #171: Preserve empty HTML tags during serialization

文書確認: https://github.com/milkshakesoftware/PreMailer.Net/tree/4fb19d5d55345cf40c331d93d3c5da74a97fde5b

**レビュー本文**: `PreserveEntitiesHtmlMarkupFormatter` should be removed, and the new EmailHtml markup formatter should be opt-in based on the options given to premailer - the option flag right now is preserveEntities - it should be something to indicate use of the opnionated html email formatter.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q43  DGP-Studio/Snap.Hutao | Add comprehensive GitHub Copilot instructions with detailed project structure, coding standards, and UI guidelines

文書確認: (リポジトリにアクセスできない)

**レビュー本文**: (なし)
- `[copilot-instructions.md]` not required, the build validation will be performed by actions
- `[copilot-instructions.md]` always targets to latest .NET SDK
- `[copilot-instructions.md]` Never introducing code behind pattern.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q44  cilium/cilium | ipsec,route: Ignore ESRCH errors on delete operations

文書確認: https://github.com/cilium/cilium/tree/325b47819b900ae2537cc8b3d45888b10b3923e1

**レビュー本文**: Overall LGTM but should we add a forbidigo rule to golangci.yaml that makes sure people don't keep using the functions that we now wrap with safenetlink?
- `[check-xfrmstate.sh]` I think the purpose of this script, IIUC, is to discourage direct calls to certain `netlink.Xfrm*` functions in pkg/datapath that would circumvent the cache. The added wrappers in safenetlink violate this, so need exclusion.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q45  OrchardCMS/OrchardCore | Migrate IContentDefinitionEventHandler to unified IContentDefinitionHandler interface

文書確認: https://github.com/OrchardCMS/OrchardCore/tree/56e062aa5d078268587015f54feb53a74c658fe7

**レビュー本文**: (なし)
- `[global.json]` Don't make changes to this file
- `[IContentDefinitionManager.cs]` this change is not needed
- `[ContentDefinitionManager.cs]` this should not be injected or used by the manager.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q46  Metta-AI/metta | feat: add MCP server

文書確認: (リポジトリにアクセスできない)

**レビュー本文**: mcp server seems like a great idea  this has ~500k lines changed -- i figure some of that's unintentional?  right now you've got custom definition of a bunch of abilities. i think that the interface for it should be a thin wrapper around the Tool interface we now have, so i dont think we should have all that many things in `src/metta/mcp_server/*.py`. the exception is stuff that queries observatory  I also think we probably dont need to commit usage examples  I think there may be changes that are unrelated to the MCP server in this PR, like experiments/marimo/policy-selector-example.py

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q47  dotnet/docs | Revise AI section

文書確認: https://github.com/dotnet/docs/tree/9c723a16d43bacf19fa905f5fdc3cfd6e2ee9169

**レビュー本文**: (なし)
- `[how-to.md]` ```suggestion You can use AI tools, such as GitHub Copilot, to generate code that serializes objects to JSON using `System.Text.Json`. For example, you can prompt Copilot to generate code that handles nested and polymorphic types, which is useful for creating examples or test data for hierarchical object structures. ```
- `[how-to.md]` These should all end in periods.
- `[how-to.md]` Now that the focus of the example has changed, seems like this belongs more in https://github.com/dotnet/docs/blob/main/docs/standard/serialization/system-text-json/polymorphism.md.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q48  rsyslog/rsyslog | Fix rsyslog issue 5957

文書確認: https://github.com/rsyslog/rsyslog/tree/556755a6e7ac29b671c35684566c9c398ab0d326

**レビュー本文**: we should keep omhttp in contrib for the time being. I intend to assign kind of tags to modules (possibly via readme), and potentially merge contrib & plugins later.

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q49  home-assistant/core | Fix Homevolt exception translation placeholders

文書確認: https://github.com/home-assistant/core/tree/e40a3e18db1e5a55ee53a7b103aab4187ad892a3

**レビュー本文**: (なし)
- `[strings.json]` Adding a translation placeholder to an existing string will cause issues for existing translations. May be it is better to use a new translation key?
- `[strings.json]` Same here

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Q50  apache/airflow | New google dataflow operator to fetch job metrics

文書確認: https://github.com/apache/airflow/tree/47ce5f32b4fae95f5865ba256d409c778d53a3d5

**レビュー本文**: I do support having such an operator, which will be an equivalent for existing sensor & trigger. However, the current implementation gives it too much responsibilities. Please refactor so it would have only one (fetching from Dataflow, without PubSub or BQ).  Also, please note that there are signals of using AI, which you did not declare in the PR. If you used AI to generate parts or the entire PR, please declare so in the PR with the required details according to the AI policy usage.
- `[dataflow.py]` I'm a bit concerned of mixing up fetching metrics **and** inserting them to PubSub or BQ altogether - it's a lot of actions for a single operator, that could be utilized by other existing operators. Please refactor so after fetching metrics - it just returns them into an XCom (and later they could be routed to PubSub/BQ using the appropriate operators).
- `[dataflow.py]` ```suggestion class DataflowJobMetricsOperator(GoogleCloudBaseOperator): ```  Rename to be consistent with existing sensor & trigger

| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |
|---|---|---|---|---|---|
|  |  |  |  |  |  |
