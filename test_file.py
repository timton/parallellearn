<button class="btn" type="submit" name="rate" value="{{ version['id'] }},{{ i }}"
                        id="{{ i }}" onmouseenter="fill({{ i }})">
                    <i class="far fa-star" id="star{{ i }}"></i>
                </button>

<form action="{{ url_for('rate') }}" method="post" class="align-center">
                    <button class="btn" type="submit" name="rate" value="{{ version['id'] }},{{ i }}">
                        <i class="far fa-star" id="{{ i }}" onmouseenter="fill({{ i)"></i>
                    </button>
                </form>