
##### Delete default remote branch
* remote default branches cannot be delete before you manually set them to another branch on the remote repo. 
Classic example is 'master' branch which first has to be changed to e.g. 'main'

```
# on the remote machine:
cd /path/to/my_git_repo 
git symbolic-ref HEAD refs/heads/new_master
```