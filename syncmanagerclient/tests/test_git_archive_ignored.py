import shutil
from pathlib import Path

import pytest

from syncmanagerclient.clients.git_archive_ignored import GitArchiveIgnoredFiles
from syncmanagerclient.util.syncconfig import SyncConfig

archive_root =  None

@pytest.fixture
def temp_repo(tmp_path):
    global archive_root
    """Create a temporary git repository for testing"""
    # Create repo directory structure
    repo_root = tmp_path / "test_repo"
    archive_root = tmp_path / "archive" / "test_repo"
    repo_root.mkdir(parents=True)
    
    # Initialize git repo
    from git import Repo
    repo = Repo.init(repo_root)
    
    # Create initial commit
    test_file = repo_root / "test.txt"
    test_file.write_text("test content")
    repo.index.add([str(test_file)])
    repo.index.commit("Initial commit")
    
    yield repo
    
    # Cleanup
    shutil.rmtree(repo.working_dir, ignore_errors=True)


@pytest.fixture
def git_archive_ignored(temp_repo, mocker):
    """Create GitArchiveIgnoredFiles instance for testing"""
    # Create a minimal mock - only set the instance attributes we need
    instance = object.__new__(GitArchiveIgnoredFiles)
    instance.local_path = Path(temp_repo.working_dir)
    mock_args = mocker.MagicMock()
    mock_args.configure_mock(sync_env='test')
    instance.config = SyncConfig(mock_args, "git")
    instance.config.dry_run = False
    # Don't call __init__ to avoid heavy initialization
    return instance


class TestNormalizeGitIgnoreEntry:
    """Tests for _normalize_gitignore_entry method"""
    
    def test_normalize_windows_path(self, git_archive_ignored):
        """Test normalization of Windows backslashes"""
        result = git_archive_ignored._normalize_gitignore_entry("subdir\\file.txt")
        assert result == "subdir/file.txt"
    
    def test_normalize_leading_dot_slash(self, git_archive_ignored):
        """Test removal of leading ./"""
        result = git_archive_ignored._normalize_gitignore_entry("./subdir")
        assert result == "subdir"
    
    def test_normalize_trailing_slash(self, git_archive_ignored):
        """Test removal of trailing slash"""
        result = git_archive_ignored._normalize_gitignore_entry("subdir/")
        assert result == "subdir"
    
    def test_normalize_combined(self, git_archive_ignored):
        """Test combined normalization"""
        result = git_archive_ignored._normalize_gitignore_entry(".\\dir/sub/")
        assert result == "dir/sub"
    
    def test_normalize_simple(self, git_archive_ignored):
        """Test simple path without special characters"""
        result = git_archive_ignored._normalize_gitignore_entry("node_modules")
        assert result == "node_modules"


class TestGitIgnorePatternToRegex:
    """Tests for _gitignore_pattern_to_regex method"""
    
    def test_wildcard_star(self, git_archive_ignored):
        """Test * wildcard matches any characters except /"""
        regex = git_archive_ignored._gitignore_pattern_to_regex("*modules")
        assert regex.fullmatch("node_modules") is not None
        assert regex.fullmatch("test_modules") is not None
        assert regex.fullmatch("dir/modules") is None
    
    def test_wildcard_question(self, git_archive_ignored):
        """Test ? wildcard matches single character"""
        regex = git_archive_ignored._gitignore_pattern_to_regex("file?.txt")
        assert regex.fullmatch("file1.txt") is not None
        assert regex.fullmatch("filea.txt") is not None
        assert regex.fullmatch("file.txt") is None
        assert regex.fullmatch("file12.txt") is None
    
    def test_char_class_positive(self, git_archive_ignored):
        """Test positive character class [a-z]"""
        regex = git_archive_ignored._gitignore_pattern_to_regex("[nN]ode_modules")
        assert regex.fullmatch("node_modules") is not None
        assert regex.fullmatch("Node_modules") is not None
        assert regex.fullmatch("xode_modules") is None
    
    def test_char_class_negative(self, git_archive_ignored):
        """Test negative character class [!a-z]"""
        regex = git_archive_ignored._gitignore_pattern_to_regex("[!n]ode_modules")
        assert regex.fullmatch("node_modules") is None
        assert regex.fullmatch("Node_modules") is not None
        assert regex.fullmatch("xode_modules") is not None
    
    def test_literal_text(self, git_archive_ignored):
        """Test literal text matching"""
        regex = git_archive_ignored._gitignore_pattern_to_regex("build")
        assert regex.fullmatch("build") is not None
        assert regex.fullmatch("Build") is None
        assert regex.fullmatch("buildx") is None
    
    def test_special_chars_escaped(self, git_archive_ignored):
        """Test escaping of regex special characters"""
        regex = git_archive_ignored._gitignore_pattern_to_regex("file.txt")
        assert regex.fullmatch("file.txt") is not None
        assert regex.fullmatch("fileXtxt") is None


class TestMatchesGitIgnorePattern:
    """Tests for _matches_gitignore_pattern method"""
    
    def test_exact_match(self, git_archive_ignored):
        """Test exact basename match"""
        assert git_archive_ignored._matches_gitignore_pattern("node_modules", "node_modules") is True
        assert git_archive_ignored._matches_gitignore_pattern("build", "dist") is False
    
    def test_wildcard_match(self, git_archive_ignored):
        """Test wildcard pattern matching"""
        assert git_archive_ignored._matches_gitignore_pattern("*modules", "node_modules") is True
        assert git_archive_ignored._matches_gitignore_pattern("*cache*", ".env.cache") is True
    
    def test_anchored_pattern(self, git_archive_ignored):
        """Test anchored pattern (leading / gets stripped)"""
        assert git_archive_ignored._matches_gitignore_pattern("/build", "build") is True
        assert git_archive_ignored._matches_gitignore_pattern("/build", "dist/build") is False
    
    def test_question_mark(self, git_archive_ignored):
        """Test ? wildcard"""
        assert git_archive_ignored._matches_gitignore_pattern("test?.log", "test1.log") is True
        assert git_archive_ignored._matches_gitignore_pattern("test?.log", "test.log") is False


class TestReadGitignorePatterns:
    """Tests for _read_gitignore_patterns method"""
    
    def test_read_empty_file(self, git_archive_ignored, temp_repo):
        """Test reading from empty .gitignore"""
        gitignore_path = Path(temp_repo.working_dir) / ".gitignore"
        gitignore_path.write_text("")
        
        patterns = git_archive_ignored._read_gitignore_patterns(gitignore_path)
        assert patterns == []
    
    def test_read_with_patterns(self, git_archive_ignored, temp_repo):
        """Test reading valid patterns"""
        gitignore_path = Path(temp_repo.working_dir) /".gitignore"
        gitignore_path.write_text("node_modules/\n*.log\nbuild/")
        
        patterns = git_archive_ignored._read_gitignore_patterns(gitignore_path)
        assert patterns == ["node_modules/", "*.log", "build/"]
    
    def test_filter_comments(self, git_archive_ignored, temp_repo):
        """Test that lines starting with # are filtered"""
        gitignore_path = Path(temp_repo.working_dir) /".gitignore"
        gitignore_path.write_text("# Comment\nnode_modules\n# Another comment")
        
        patterns = git_archive_ignored._read_gitignore_patterns(gitignore_path)
        assert patterns == ["node_modules"]
    
    def test_filter_empty_lines(self, git_archive_ignored, temp_repo):
        """Test that empty lines are filtered"""
        gitignore_path = Path(temp_repo.working_dir) /".gitignore"
        gitignore_path.write_text("\nnode_modules\n\nbuild\n")
        
        patterns = git_archive_ignored._read_gitignore_patterns(gitignore_path)
        assert patterns == ["node_modules", "build"]
    
    def test_filter_negation_patterns(self, git_archive_ignored, temp_repo):
        """Test that negation patterns starting with ! are filtered"""
        gitignore_path = Path(temp_repo.working_dir) /".gitignore"
        gitignore_path.write_text("*.log\n!important.log\n*.tmp")
        
        patterns = git_archive_ignored._read_gitignore_patterns(gitignore_path)
        assert patterns == ["*.log", "*.tmp"]
    
    def test_combined_filters(self, git_archive_ignored, temp_repo):
        """Test all filters together"""
        gitignore_path = Path(temp_repo.working_dir) / ".gitignore"
        gitignore_path.write_text("""
# Comments section

node_modules/

!important/

build/

# End comment
""")
        
        patterns = git_archive_ignored._read_gitignore_patterns(gitignore_path)
        assert patterns == ["node_modules/", "build/"]


class TestReadGitignoreEntries:
    """Tests for _read_gitignore_entries method"""
    
    def test_read_entries_for_duplicate_check(self, git_archive_ignored, temp_repo):
        """Test reading entries as normalized set"""
        gitignore_path = Path(temp_repo.working_dir) /".gitignore"
        gitignore_path.write_text("node_modules/\nbuild/\n*.log")
        
        entries = git_archive_ignored._read_gitignore_entries(gitignore_path)
        assert "node_modules" in entries
        assert "build" in entries
        assert "*.log" in entries
        assert len(entries) == 3
    
    def test_filters_comments_and_empty_and_negation(self, git_archive_ignored, temp_repo):
        """Test that all filters apply to entries"""
        gitignore_path = Path(temp_repo.working_dir) /".gitignore"
        gitignore_path.write_text("# comment\n\nnode_modules\n!keep.log\nbuild/")
        
        entries = git_archive_ignored._read_gitignore_entries(gitignore_path)
        assert entries == {"node_modules", "build"}


class TestFindGitignoreFilesForPath:
    """Tests for _find_gitignore_files_for_path method"""
    
    def test_finds_gitignore_in_current_dir(self, git_archive_ignored, temp_repo):
        """Test finds .gitignore in the immediate directory"""
        subdir = Path(temp_repo.working_dir) /"subdir"
        subdir.mkdir()
        gitignore = subdir / ".gitignore"
        gitignore.write_text("*.log")
        
        files = git_archive_ignored._find_gitignore_files_for_path(subdir)
        assert len(files) == 1
        assert files[0] == gitignore
    
    def test_finds_gitignore_in_parent_dirs(self, git_archive_ignored, temp_repo):
        """Test finds .gitignore files up the directory tree"""
        subdir = Path(temp_repo.working_dir) /"a" / "b"
        subdir.mkdir(parents=True)
        
        # Create multiple .gitignore files
        gitignore_root = Path(temp_repo.working_dir) /".gitignore"
        gitignore_root.write_text("node_modules/")
        
        gitignore_a = Path(temp_repo.working_dir) /"a" / ".gitignore"
        gitignore_a.write_text("*.log")
        
        gitignore_b = subdir / ".gitignore"
        gitignore_b.write_text("build/")
        
        files = git_archive_ignored._find_gitignore_files_for_path(subdir)
        assert len(files) == 3
        assert gitignore_b in files
        assert gitignore_a in files
        assert gitignore_root in files
        # Order: nearest first
        assert files[0] == gitignore_b
        assert files[1] == gitignore_a
        assert files[2] == gitignore_root
    
    def test_no_gitignore_files(self, git_archive_ignored, temp_repo):
        """Test when no .gitignore files exist"""
        subdir = Path(temp_repo.working_dir) /"subdir"
        subdir.mkdir()
        
        files = git_archive_ignored._find_gitignore_files_for_path(subdir)
        assert files == []
    
    def test_stops_at_repo_root(self, git_archive_ignored, temp_repo):
        """Test doesn't search beyond repository root"""
        subdir = Path(temp_repo.working_dir) /"subdir"
        subdir.mkdir()
        gitignore_root = Path(temp_repo.working_dir) /".gitignore"
        gitignore_root.write_text("node_modules/")
        
        files = git_archive_ignored._find_gitignore_files_for_path(subdir)
        assert len(files) == 1
        assert files[0] == gitignore_root


class TestExtendGitIgnore:
    """Integration tests for extend_git_ignore method"""
    
    def test_adds_directory_without_match(self, git_archive_ignored, temp_repo):
        """Test adding directory that has no matching pattern"""
        # Create ignored directory
        to_ignore_symlink = self.construct_symlink(temp_repo, "my_cache")

        gitignore = Path(Path(temp_repo.working_dir)) / ".gitignore"

        gitignore.write_text("node_modules/")
        
        # Call extend_git_ignore
        git_archive_ignored.extend_git_ignore_file([str(to_ignore_symlink.relative_to(Path(temp_repo.working_dir)))])

        # Verify .gitignore was updated
        content = gitignore.read_text()
        assert "my_cache" in content
        assert "node_modules/" in content
    
    def test_skips_directory_with_exact_match(self, git_archive_ignored, temp_repo):
        """Test not adding directory when exact pattern matches"""
        to_ignore_symlink = self.construct_symlink(temp_repo,  "node_modules")

        gitignore = Path(temp_repo.working_dir) / ".gitignore"

        gitignore.write_text("node_modules")
        
        original_content = gitignore.read_text()
        git_archive_ignored.extend_git_ignore_file([str(to_ignore_symlink.relative_to(Path(temp_repo.working_dir)))])

        # Should not add duplicate
        assert gitignore.read_text() == original_content
    
    def test_skips_directory_with_wildcard_match(self, git_archive_ignored, temp_repo):
        """Test not adding directory when wildcard pattern matches"""
        to_ignore_symlink = self.construct_symlink(temp_repo,  "my_modules")

        gitignore = Path(temp_repo.working_dir) / ".gitignore"

        gitignore.write_text("*modules")
        
        original_content = gitignore.read_text()
        git_archive_ignored.extend_git_ignore_file([str(to_ignore_symlink.relative_to(Path(temp_repo.working_dir)))])

        assert gitignore.read_text() == original_content
    
    def test_directory_only_pattern_no_match(self, git_archive_ignored, temp_repo):
        """Test that 'pattern/' doesn't match directory without trailing slash"""
        """
        Critical: If pattern ends with '/' and basename doesn't, and they're otherwise identical
        → do NOT match (e.g., 'node_modules/' should NOT match 'node_modules')
        """
        # Create a directory WITHOUT trailing slash in name (normal directory)
        to_ignore_symlink = self.construct_symlink(temp_repo,  "node_modules")

        # Create .gitignore with pattern ending with /
        gitignore = Path(temp_repo.working_dir) /".gitignore"
        gitignore.write_text("node_modules/")
        
        # The directory 'node_modules' (basename without /) should NOT match pattern 'node_modules/'
        # because the pattern explicitly requires a directory ending
        git_archive_ignored.extend_git_ignore_file([str(to_ignore_symlink.relative_to(Path(temp_repo.working_dir)))])

        # Should add it since 'node_modules/' != 'node_modules' for matching purposes
        content = gitignore.read_text()
        assert "node_modules/" in content
    
    def test_uses_nearest_gitignore(self, git_archive_ignored, temp_repo):
        """Test adding to nearest .gitignore file in hierarchy"""
        subdir = Path(temp_repo.working_dir) / "subdir"
        to_ignore_symlink = self.construct_symlink(temp_repo,  "subdir/cache")

        # Create .gitignore in parent directory
        gitignore_sub = subdir / ".gitignore"
        gitignore_sub.write_text("*.log")
        
        gitignore_root = Path(temp_repo.working_dir) /".gitignore"
        gitignore_root.write_text("node_modules/")
        
        # Should add to nearest .gitignore (subdir/.gitignore)
        git_archive_ignored.extend_git_ignore_file([str(to_ignore_symlink.relative_to(Path(temp_repo.working_dir)))])

        content_sub = gitignore_sub.read_text()
        assert "cache" in content_sub
        
        content_root = gitignore_root.read_text()
        assert "cache" not in content_root
    
    def test_fallback_to_root_gitignore(self, git_archive_ignored, temp_repo):
        """Test falling back to root .gitignore when none in path"""

        to_ignore_symlink = self.construct_symlink(temp_repo,  "deep/cache")

        gitignore_root = Path(temp_repo.working_dir) / ".gitignore"
        gitignore_root.write_text("node_modules/")
        
        # Should add to root .gitignore since no .gitignore in the path
        git_archive_ignored.extend_git_ignore_file([str(to_ignore_symlink.relative_to(Path(temp_repo.working_dir)))])

        content = gitignore_root.read_text()
        assert "deep/cache" in content
    
    def test_prevents_duplicates_in_same_file(self, git_archive_ignored, temp_repo):
        """Test that duplicate entries are not added to same .gitignore"""
        gitignore = Path(temp_repo.working_dir) /".gitignore"
        gitignore.write_text("cache/")
        
        # Try to add same directory twice
        git_archive_ignored.extend_git_ignore_file(["cache"])
        git_archive_ignored.extend_git_ignore_file(["cache"])
        
        content = gitignore.read_text()
        # Count occurrences of "cache/"
        count = content.count("cache/")
        assert count == 1
    
    def test_multiple_directories(self, git_archive_ignored, temp_repo):
        """Test adding multiple directories at once"""
        to_ignore_symlink1 = self.construct_symlink(temp_repo,  "cache1")
        to_ignore_symlink2 = self.construct_symlink(temp_repo,  "cache2")


        gitignore = Path(temp_repo.working_dir) / ".gitignore"

        gitignore.write_text("node_modules/")
        
        git_archive_ignored.extend_git_ignore_file([
            str(to_ignore_symlink1.relative_to(Path(temp_repo.working_dir))),
            str(to_ignore_symlink2.relative_to(Path(temp_repo.working_dir)))
        ])
        
        content = gitignore.read_text()
        assert "cache1" in content
        assert "cache2" in content
    
    def test_check_hierarchical_gitignore_first(self, git_archive_ignored, temp_repo):
        """Test that hierarchical .gitignore is checked before adding"""
        # Structure: .gitignore at root with "*" pattern
        gitignore_root = Path(temp_repo.working_dir) /".gitignore"
        gitignore_root.write_text("*")

        to_ignore_symlink = self.construct_symlink(temp_repo,  "subdir/anything")

        # Should NOT add because root .gitignore has "*" which matches everything
        original_content = gitignore_root.read_text()
        git_archive_ignored.extend_git_ignore_file([str(to_ignore_symlink.relative_to(Path(temp_repo.working_dir)))])
        assert gitignore_root.read_text() == original_content
    
    def test_relative_path_handling(self, git_archive_ignored, temp_repo):
        """Test that relative paths are handled correctly"""
        to_ignore_symlink = self.construct_symlink(temp_repo,  "a/b/c")

        gitignore = Path(temp_repo.working_dir) / ".gitignore"
        gitignore.write_text("")

        git_archive_ignored.extend_git_ignore_file([str(to_ignore_symlink.relative_to(Path(temp_repo.working_dir)))])

        content = gitignore.read_text()
        assert "a/b/c" in content
    
    def test_utf8_encoding(self, git_archive_ignored, temp_repo):
        """Test that UTF-8 encoding is used"""
        utf_dir_to_ignore_symlink = self.construct_symlink(temp_repo,  "кириллица")

        gitignore = Path(temp_repo.working_dir) / ".gitignore"
        gitignore.write_text("", encoding='utf-8')

        git_archive_ignored.extend_git_ignore_file([str(utf_dir_to_ignore_symlink.relative_to(Path(temp_repo.working_dir)))])

        # Should be able to read with UTF-8
        content = gitignore.read_text(encoding='utf-8')
        assert "кириллица" in content


    def construct_symlink(self, temp_repo, rel_path_str):
        target_dir = Path(archive_root).joinpath(*rel_path_str.split("/"))
        target_dir.mkdir(parents=True, exist_ok=True)
        to_ignore_symlink = Path(temp_repo.working_dir) / rel_path_str
        to_ignore_symlink.parent.mkdir(parents=True, exist_ok=True)
        to_ignore_symlink.symlink_to(archive_root)
        return to_ignore_symlink

